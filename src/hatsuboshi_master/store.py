"""Validated SQLCipher/protobuf export and atomic versioned snapshots."""
from concurrent.futures import ThreadPoolExecutor
import fcntl
import hashlib
import inspect
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import uuid

import requests
import yaml
from google.protobuf.json_format import MessageToDict
from .schema import SCHEMA, message

NAME = re.compile(r'[A-Za-z][A-Za-z0-9_]*\Z')

class SchemaMismatch(ValueError):
    pass

def as_dict(record):
    options = {'preserving_proto_field_name': True}
    if 'always_print_fields_with_no_presence' in inspect.signature(MessageToDict).parameters:
        options['always_print_fields_with_no_presence'] = True
    else:
        options['including_default_value_fields'] = True
    return MessageToDict(record, **options)

def decode_record(pool, name, data):
    record = message(pool, 'pmaster.' + name)
    record.ParseFromString(data)
    before = record.SerializeToString(deterministic=True)
    record.DiscardUnknownFields()
    if before != record.SerializeToString(deterministic=True):
        raise SchemaMismatch(f'{name}: unknown protobuf fields; export a current schema')
    return as_dict(record)

def export_table(pool, pack, raw, output):
    from sqlcipher3 import dbapi2 as sqlite
    if not re.fullmatch(r'[0-9a-fA-F]{64}', pack.cryptoKey):
        raise ValueError(f'{pack.type}: invalid database key')
    connection = sqlite.connect(str(raw))
    try:
        connection.execute(f'PRAGMA key = "x\'{pack.cryptoKey}\'"')
        connection.execute('PRAGMA query_only = ON')
        records = [decode_record(pool, pack.type, bytes(row[0]))
                   for row in connection.execute(f'SELECT data FROM "{pack.type}" ORDER BY rowid')]
    finally:
        connection.close()
    json_bytes = (json.dumps(records, ensure_ascii=False, separators=(',', ':')) + '\n').encode()
    (output / 'json' / (pack.type + '.json')).write_bytes(json_bytes)
    yaml_bytes = yaml.dump(records, Dumper=yaml.CSafeDumper, allow_unicode=True, sort_keys=False).encode()
    (output / (pack.type + '.yaml')).write_bytes(yaml_bytes)
    return {'rows': len(records), 'sha256': hashlib.sha256(yaml_bytes).hexdigest()}

def download(pack, target):
    from urllib.parse import urlparse
    if urlparse(pack.downloadUrl).scheme != 'https':
        raise ValueError(f'{pack.type}: download must use HTTPS')
    with requests.get(pack.downloadUrl, timeout=(15, 120), stream=True) as response:
        if not response.ok:
            raise RuntimeError(f'{pack.type}: download HTTP {response.status_code}')
        size = 0
        with target.open('wb') as f:
            for chunk in response.iter_content(1024 * 1024):
                size += len(chunk)
                if size > pack.fileSize:
                    raise ValueError(f'{pack.type}: download exceeds declared size')
                f.write(chunk)
    if size != pack.fileSize:
        raise ValueError(f'{pack.type}: incomplete download')

def validate_manifest(pool, manifest):
    packs = list(manifest.masterTag.masterTagPacks)
    if not packs or not manifest.masterTag.version:
        raise ValueError('Empty master manifest')
    names = [p.type for p in packs]
    if len(names) != len(set(names)) or any(not NAME.fullmatch(n) for n in names):
        raise ValueError('Invalid or duplicate table names')
    missing = []
    for pack in packs:
        try:
            pool.FindMessageTypeByName('pmaster.' + pack.type)
        except KeyError:
            missing.append(pack.type)
        if pack.fileSize <= 0:
            raise ValueError(f'{pack.type}: invalid database size')
    if missing:
        raise SchemaMismatch('Missing protobuf tables: ' + ', '.join(sorted(missing)))
    return packs

def valid_snapshot(path, version, schema_hash, names):
    try:
        state = json.loads((path / 'snapshot.json').read_text())
        return (state['version'] == version and state['schema_sha256'] == schema_hash
                and set(state['tables']) == set(names)
                and all(hashlib.sha256((path / (n + '.yaml')).read_bytes()).hexdigest() == v['sha256']
                        for n, v in state['tables'].items()))
    except (OSError, ValueError, KeyError):
        return False

def update_snapshot(root, pool, manifest, *, schema=SCHEMA, workers=4, force=False, downloader=download, exporter=export_table):
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    with (root / 'update.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        packs = validate_manifest(pool, manifest)
        version = manifest.masterTag.version
        schema_hash = hashlib.sha256(Path(schema).read_bytes()).hexdigest()
        current = root / 'current'
        if not force and valid_snapshot(current, version, schema_hash, [p.type for p in packs]):
            return current.resolve()
        releases = root / 'versions'
        releases.mkdir(exist_ok=True)
        stage = Path(tempfile.mkdtemp(prefix='.staging-', dir=releases))
        stage.chmod(0o755)
        try:
            (stage / 'raw').mkdir(mode=0o700)
            (stage / 'json').mkdir()
            def process(pack):
                raw = stage / 'raw' / pack.type
                downloader(pack, raw)
                result = exporter(pool, pack, raw, stage)
                raw.unlink()
                return pack.type, result
            with ThreadPoolExecutor(max_workers=max(1, min(workers, 8))) as executor:
                tables = dict(executor.map(process, packs))
            (stage / 'raw').rmdir()
            state = {'version': version, 'schema_sha256': schema_hash, 'tables': tables}
            (stage / 'snapshot.json').write_text(json.dumps(state, sort_keys=True, indent=2) + '\n')
            final = releases / (hashlib.sha256(version.encode()).hexdigest()[:16] + '-' + uuid.uuid4().hex[:8])
            os.replace(stage, final)
            link = root / ('.current-' + uuid.uuid4().hex)
            try:
                link.symlink_to(final.relative_to(root), target_is_directory=True)
                os.replace(link, current)
            finally:
                link.unlink(missing_ok=True)
            return final
        finally:
            if stage.exists():
                shutil.rmtree(stage)
