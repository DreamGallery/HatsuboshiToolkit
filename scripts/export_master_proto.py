#!/usr/bin/env python3
"""Export a descriptor set from a current, locally extracted Il2CppDumper dump.cs.
Requires Docker, git and the optional grpcio-tools package. No game account needed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

CAMPUS_COMMIT = 'a7f5b047b47594761c9623117f4f8aa159ba38c6'
FILES = ['penum.proto', 'pcommon.proto', 'pmaster.proto', 'ptransaction.proto', 'papicommon.proto', 'papi.proto']

def run(*args, **kwargs):
    subprocess.run([str(a) for a in args], check=True, **kwargs)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dump', required=True, type=Path)
    parser.add_argument('--game-version', required=True)
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[1]/'src/hatsuboshi_master/proto')
    args=parser.parse_args()
    dump=args.dump.resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix='hatsuboshi-schema-') as temporary:
        root=Path(temporary);campus=root/'campus'
        run('git','clone','https://github.com/vertesan/campus.git',campus)
        run('git','-C',campus,'checkout','--detach',CAMPUS_COMMIT)
        (campus/'cache').mkdir(exist_ok=True)
        shutil.copy2(dump,campus/'cache/dump.cs')
        command=campus/'cmd/schema-export';command.mkdir(parents=True)
        (command/'main.go').write_text('package main\nimport "vertesan/campus/analyser"\nfunc main() { analyser.Analyze() }\n')
        run('docker','run','--rm','-v',f'{campus}:/work','-w','/work','golang:1.25','go','run','./cmd/schema-export')
        generated=campus/'cache/GeneratedProto'
        run(sys.executable,'-m','grpc_tools.protoc',f'-I{generated}','--include_imports',
            f'--descriptor_set_out={generated}/schema.pb',*[generated/name for name in FILES])
        provenance={'game_version':args.game_version,'campus_commit':CAMPUS_COMMIT,
                    'dump_sha256':hashlib.sha256(dump.read_bytes()).hexdigest()}
        (generated/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
        args.output.mkdir(parents=True,exist_ok=True)
        for name in FILES+['schema.pb','provenance.json']:
            shutil.copy2(generated/name,args.output/name)
    print('Schema exported; run the masterdb validation tests before publishing.')

if __name__=='__main__':main()
