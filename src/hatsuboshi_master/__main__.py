import argparse
import json
import os
from pathlib import Path
import re
import sys
import time
import requests
from .client import Client
from .schema import SCHEMA, load_pool, message
from .store import SchemaMismatch, update_snapshot


def app_version(explicit=None):
    if explicit:
        if not re.fullmatch(r'\d+\.\d+\.\d+', explicit):
            raise ValueError('Invalid app version')
        return explicit
    response = requests.get('https://play.google.com/store/apps/details',
        params={'id': 'com.bandainamcoent.idolmaster_gakuen', 'hl': 'ja'}, timeout=30)
    response.raise_for_status()
    match = re.search(r'\[\[\["([\d.]+)"\]\],\[\[\[\d+\]\],\[\[\[\d+,"', response.text)
    if not match:
        raise ValueError('Cannot detect game version; set HATSUBOSHI_APP_VERSION')
    return match[1]


def main(argv=None):
    p = argparse.ArgumentParser(description='Download and validate game masterdb; publish an atomic YAML/JSON snapshot')
    p.add_argument('--output', type=Path, default=Path(os.getenv('HATSUBOSHI_MASTER_ROOT', 'cache/masterdb')))
    p.add_argument('--credentials', type=Path, default=os.getenv('HATSUBOSHI_CREDENTIALS_FILE'))
    p.add_argument('--app-version', default=os.getenv('HATSUBOSHI_APP_VERSION'))
    p.add_argument('--schema', type=Path, default=SCHEMA)
    p.add_argument('--manifest', type=Path, help='Offline MasterGetResponse protobuf (contains download keys; keep private)')
    p.add_argument('--interval', type=int, default=0, help='Seconds between checks; 0 runs once')
    p.add_argument('--workers', type=int, default=4)
    p.add_argument('--force', action='store_true')
    args = p.parse_args(argv)
    if args.interval < 0 or (args.interval and args.interval < 60):
        p.error('interval must be 0 or at least 60 seconds')
    if not args.manifest and not args.credentials:
        p.error('provide --credentials or HATSUBOSHI_CREDENTIALS_FILE')
    while True:
        try:
            pool = load_pool(args.schema)
            if args.manifest:
                manifest = message(pool, 'client.api.MasterGetResponse').FromString(args.manifest.read_bytes())
            else:
                client = Client(pool, app_version(args.app_version))
                try:
                    client.login(args.credentials)
                    manifest = client.manifest()
                finally:
                    client.close()
            result = update_snapshot(args.output, pool, manifest, schema=args.schema, workers=args.workers, force=args.force)
            state = json.loads((result / 'snapshot.json').read_text())
            print(json.dumps({'version':state['version'], 'tables':len(state['tables']), 'path':str(result)}, ensure_ascii=False), flush=True)
        except Exception as exc:
            # Network exceptions may contain signed URLs or credentials.
            detail = str(exc) if isinstance(exc, SchemaMismatch) else type(exc).__name__
            print('Masterdb update failed: ' + detail, file=sys.stderr, flush=True)
            if not args.interval:
                return 1
        if not args.interval:
            return 0
        time.sleep(args.interval)

if __name__ == '__main__':
    raise SystemExit(main())
