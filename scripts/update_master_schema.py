#!/usr/bin/env python3
"""Export checked masterdb schemas from an Android APK or XAPK package."""
import argparse
import hashlib
import json
import mmap
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import struct
import subprocess
import sys
import tempfile
from urllib.parse import urljoin, urlsplit
import zipfile

import requests

from validate_master_schema import FILES, validate

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = 'com.bandainamcoent.idolmaster_gakuen'
DUMPER_VERSION = 'v6.7.46'
DUMPER_URL = f'https://github.com/Perfare/Il2CppDumper/releases/download/{DUMPER_VERSION}/Il2CppDumper-net6-{DUMPER_VERSION}.zip'
DUMPER_SHA256 = 'db9bbbc538e33abfb057c7757ae5d6c1f16a05fdc0d13af8a5a67ea31faaba0c'
MAX_PACKAGE = 3 * 1024**3
MAX_MEMBER = 1024**3
MAGIC = b'\xaf\x1b\xb1\xfa'
ABIS = ('arm64-v8a', 'armeabi-v7a', 'x86_64', 'x86')


def sha256(path):
    with Path(path).open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def download(url, target, limit=MAX_PACKAGE, expected=None):
    """Only write a complete HTTPS download; never log URLs with signed queries."""
    target = Path(target)
    temporary = target.with_suffix(target.suffix + '.part')
    try:
        with requests.Session() as session:
            session.headers['User-Agent'] = 'HatsuboshiToolkit/schema-update'
            for _ in range(6):
                parsed = urlsplit(url)
                if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
                    raise ValueError('Package URL and redirects must use HTTPS without embedded credentials')
                with session.get(url, stream=True, allow_redirects=False, timeout=(20, 120)) as response:
                    if response.is_redirect:
                        url = urljoin(url, response.headers['Location'])
                        continue
                    if response.status_code != 200:
                        raise ValueError(f'Download returned HTTP {response.status_code}')
                    size = 0
                    with temporary.open('wb') as output:
                        for block in response.iter_content(1024 * 1024):
                            size += len(block)
                            if size > limit:
                                raise ValueError('Download exceeds the size limit')
                            output.write(block)
                    if not size:
                        raise ValueError('Empty download')
                    if expected and sha256(temporary) != expected.lower():
                        raise ValueError('Download SHA-256 does not match')
                    temporary.replace(target)
                    return
            raise ValueError('Too many download redirects')
    except requests.RequestException as exc:
        raise RuntimeError(f'Download failed ({type(exc).__name__})') from None
    finally:
        temporary.unlink(missing_ok=True)


def copy_member(archive, info, output, limit=MAX_MEMBER):
    if info.file_size > limit or info.flag_bits & 1:
        raise ValueError('Unsupported or oversized archive member')
    with archive.open(info) as source, Path(output).open('wb') as target:
        shutil.copyfileobj(source, target, 1024 * 1024)


def android_tool(explicit=None):
    if explicit:
        return str(Path(explicit).resolve(strict=True))
    found = shutil.which('aapt2')
    if found:
        return found
    sdk = os.getenv('ANDROID_HOME') or os.getenv('ANDROID_SDK_ROOT')
    if sdk:
        candidates = list((Path(sdk) / 'build-tools').glob('*/aapt2'))
        if candidates:
            return str(max(candidates, key=lambda p: tuple(int(n) for n in re.findall(r'\d+', p.parent.name))))
    raise ValueError('Android SDK aapt2 is required; set ANDROID_HOME or --aapt2')


def apk_identity(apk, aapt2):
    result = subprocess.run([aapt2, 'dump', 'badging', str(apk)], capture_output=True,
                            text=True, timeout=120, check=True)
    line = next((line for line in result.stdout.splitlines() if line.startswith('package: ')), '')
    fields = dict(re.findall(r"(\w+)='([^']*)'", line))
    if fields.get('name') != PACKAGE or not fields.get('versionCode', '').isdigit():
        raise ValueError('Archive does not contain the expected game package')
    return fields


def extract_client(package, directory, aapt2):
    directory.mkdir(parents=True)
    with zipfile.ZipFile(package) as archive:
        if 'AndroidManifest.xml' in archive.namelist():
            apks = [Path(package)]
        else:
            members = [info for info in archive.infolist() if info.filename.lower().endswith('.apk')]
            if not members or len(members) > 100 or sum(info.file_size for info in members) > 4 * 1024**3:
                raise ValueError('Expected an APK or XAPK containing game APK files')
            apks = []
            for index, info in enumerate(members):
                apk = directory / f'part-{index}.apk'
                copy_member(archive, info, apk)
                apks.append(apk)
    identities, files = [], {}
    for apk in apks:
        identities.append(apk_identity(apk, aapt2))
        with zipfile.ZipFile(apk) as archive:
            for info in archive.infolist():
                name = PurePosixPath(info.filename)
                if name.name == 'global-metadata.dat':
                    key = 'metadata'
                elif len(name.parts) == 3 and name.parts[0] == 'lib' and name.parts[1] in ABIS and name.name == 'libil2cpp.so':
                    key = name.parts[1]
                else:
                    continue
                path = directory / f'{key}.bin'
                if key in files:
                    duplicate = directory / 'duplicate.bin'
                    copy_member(archive, info, duplicate)
                    if sha256(duplicate) != sha256(files[key]):
                        raise ValueError(f'Conflicting client files: {key}')
                    duplicate.unlink()
                else:
                    copy_member(archive, info, path)
                    files[key] = path
    codes = {item['versionCode'] for item in identities}
    versions = {item['versionName'] for item in identities if item.get('versionName')}
    if len(codes) != 1 or len(versions) != 1:
        raise ValueError('APK parts must belong to one client version and include the base APK')
    version = versions.pop()
    if not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise ValueError('Invalid game version in Android manifest')
    abi = next((abi for abi in ABIS if abi in files), None)
    if 'metadata' not in files or abi is None:
        raise ValueError('Package is missing metadata or libil2cpp.so; provide the complete APK/XAPK')
    return files['metadata'], files[abi], {
        'game_version': version, 'version_code': int(codes.pop()),
        'package_name': PACKAGE, 'platform': f'Android {abi}',
    }


def metadata_header(data, size):
    if len(data) < 256 or data[:4] != MAGIC:
        return None
    version, header_size = struct.unpack_from('<II', data, 4)
    if not 24 <= version <= 40 or not 128 <= header_size <= len(data) or header_size % 8:
        return None
    pairs = [struct.unpack_from('<II', data, offset) for offset in range(8, header_size, 8)]
    if not all(offset <= size and length <= size - offset and
               (not length or offset >= header_size) for offset, length in pairs):
        return None
    if not all(length for _, length in pairs[:3]):
        return None
    return version


def restore_metadata(source, library, output):
    data = Path(source).read_bytes()
    version = metadata_header(data[:8192], len(data))
    if version:
        Path(output).write_bytes(data)
        return version
    if len(data) < 256:
        raise ValueError('Metadata file is too short')
    prefix = bytes(value ^ plain for value, plain in zip(data[:4], MAGIC))
    masks = set()
    with Path(library).open('rb') as source_library:
        with mmap.mmap(source_library.fileno(), 0, access=mmap.ACCESS_READ) as binary:
            if binary[:4] != b'\x7fELF':
                raise ValueError('Expected an Android ELF library')
            start = 0
            while (offset := binary.find(prefix, start)) >= 0:
                start = offset + 1
                mask = binary[offset:offset + 128]
                if len(mask) != 128:
                    continue
                header = bytes(value ^ mask[i % 128] for i, value in enumerate(data[:8192]))
                if metadata_header(header, len(data)):
                    masks.add(mask)
    if len(masks) != 1:
        raise ValueError('Cannot uniquely restore metadata from this client; manual parser update required')
    mask = masks.pop()
    result = bytearray(data)
    for phase, key in enumerate(mask):
        table = bytes(value ^ key for value in range(256))
        result[phase::128] = data[phase::128].translate(table)
    version = metadata_header(result[:8192], len(result))
    Path(output).write_bytes(result)
    return version


def prepare_dumper(directory):
    directory.mkdir(parents=True, exist_ok=True)
    package = directory / 'Il2CppDumper.zip'
    if not package.is_file() or sha256(package) != DUMPER_SHA256:
        download(DUMPER_URL, package, limit=32 * 1024**2, expected=DUMPER_SHA256)
    with zipfile.ZipFile(package) as archive:
        for info in archive.infolist():
            if not info.is_dir() and '/' not in info.filename and '\\' not in info.filename:
                copy_member(archive, info, directory / info.filename, limit=32 * 1024**2)
    config = directory / 'config.json'
    settings = json.loads(config.read_text())
    settings.update(RequireAnyKey=False, GenerateDummyDll=False, GenerateScript=False, GenerateStruct=False)
    config.write_text(json.dumps(settings))
    return directory / 'Il2CppDumper.dll'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--url', help='Direct HTTPS download URL for APK/XAPK')
    source.add_argument('--archive', type=Path, help='Local APK/XAPK')
    parser.add_argument('--sha256', help='Optional expected package checksum')
    parser.add_argument('--work-dir', type=Path, default=ROOT / '.agent-local/schema-update')
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--aapt2')
    parser.add_argument('--dotnet', default='dotnet')
    args = parser.parse_args()
    if args.sha256 and not re.fullmatch('[0-9a-fA-F]{64}', args.sha256):
        parser.error('--sha256 must contain 64 hexadecimal characters')
    work = args.work_dir.resolve()
    work.mkdir(parents=True, exist_ok=True)
    aapt2 = android_tool(args.aapt2)
    with tempfile.TemporaryDirectory(prefix='client-', dir=work) as temporary:
        stage = Path(temporary)
        package = args.archive.resolve(strict=True) if args.archive else stage / 'client.zip'
        if args.url:
            print('Downloading game package', flush=True)
            download(args.url, package, expected=args.sha256)
        elif args.sha256 and sha256(package) != args.sha256.lower():
            raise ValueError('Package SHA-256 does not match')
        metadata, library, provenance = extract_client(package, stage / 'client', aapt2)
        baseline = ROOT / 'src/hatsuboshi_master/proto'
        previous = json.loads((baseline / 'provenance.json').read_text())
        if tuple(map(int, provenance['game_version'].split('.'))) < tuple(map(int, previous['game_version'].split('.'))):
            raise ValueError('Client is older than the published schema')
        print(f"Client {provenance['game_version']} ({provenance['version_code']}), {provenance['platform']}", flush=True)
        restored = stage / 'global-metadata.dat'
        version = restore_metadata(metadata, library, restored)
        print(f'Metadata validated (version {version})', flush=True)
        dumper = prepare_dumper(work / 'tools')
        dump_dir = stage / 'dump'
        dump_dir.mkdir()
        subprocess.run([args.dotnet, str(dumper), str(library), str(restored), str(dump_dir)],
                       check=True, timeout=900, env={**os.environ, 'DOTNET_ROLL_FORWARD': 'Major'})
        dump = dump_dir / 'dump.cs'
        if not dump.is_file() or not dump.stat().st_size:
            raise ValueError('Il2CppDumper did not produce dump.cs')
        generated = stage / 'proto'
        subprocess.run([sys.executable, str(ROOT / 'scripts/export_master_proto.py'), '--dump', str(dump),
                        '--game-version', provenance['game_version'], '--output', str(generated)],
                       check=True, timeout=1200, env={**os.environ, 'TMPDIR': str(stage)})
        report = validate(generated / 'schema.pb', baseline / 'schema.pb')
        provenance.update(json.loads((generated / 'provenance.json').read_text()))
        provenance.update(metadata_version=version, il2cpp_dumper=DUMPER_VERSION,
                          source='Android APK/XAPK', input_sha256={
                              'package': sha256(package), 'libil2cpp.so': sha256(library),
                              'global-metadata.dat': sha256(metadata),
                              'global-metadata-decrypted.dat': sha256(restored),
                          })
        (generated / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
        args.output.mkdir(parents=True, exist_ok=True)
        for name in (*FILES, 'schema.pb', 'provenance.json'):
            shutil.copy2(generated / name, args.output / name)
        print(f"Schema validated: {len(report['added_messages'])} added messages, {report['added_fields']} added fields", flush=True)
        if summary := os.getenv('GITHUB_STEP_SUMMARY'):
            with Path(summary).open('a') as file:
                file.write(f"Client: **{provenance['game_version']}** ({provenance['version_code']})\n\n")
                file.write(f"Schema validation passed: {len(report['added_messages'])} added messages, {report['added_fields']} added fields.\n")


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        # Signed download URLs and third-party subprocess output must not leak in tracebacks.
        detail = str(exc) if isinstance(exc, (ValueError, RuntimeError)) else type(exc).__name__
        print('Schema update failed: ' + detail, file=sys.stderr)
        raise SystemExit(1)
