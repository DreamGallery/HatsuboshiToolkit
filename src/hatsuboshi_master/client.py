"""Minimal login and Master/Get. Does not claim bonuses or enter gameplay."""
import json
import os
from pathlib import Path
import tempfile
import time
import grpc
import requests
from .codec import encode, decode
from .schema import message

FIREBASE_KEY = 'AIzaSyCe_vKRW5Pc0rTXFksur-ZCDb_kRCxNhng'
FIREBASE_HEADERS = {'X-Android-Package': 'com.bandainamcoent.idolmaster_gakuen',
                    'X-Android-Cert': 'D05C4DC398804FEB2ADF30E8854500D2834EAFED'}

def save_credentials(path, credentials):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(credentials, f)
        os.replace(temp, path)
    finally:
        Path(temp).unlink(missing_ok=True)

def firebase_request(endpoint, payload):
    response = requests.post(endpoint + '?key=' + FIREBASE_KEY, json=payload,
                             headers=FIREBASE_HEADERS, timeout=30)
    if not response.ok:
        raise RuntimeError(f'Firebase HTTP {response.status_code}')
    return response.json()

class Client:
    def __init__(self, pool, app_version):
        self.pool = pool
        self.channel = grpc.secure_channel('api.game-gakuen-idolmaster.jp:443', grpc.ssl_channel_credentials(),
            options=[('grpc.default_authority', 'api.game-gakuen-idolmaster.jp'),
                     ('grpc.primary_user_agent', 'grpc-csharp/2.37.0-dev grpc-c/15.0.0 (android; chttp2)'),
                     ('grpc.max_receive_message_length', 16 * 1024 * 1024)])
        self.headers = {'x-platform': 'Android', 'x-device-name': 'Pixel 9 Pro XL',
            'x-os-version': 'Android OS 13 / API-33', 'accept-language': 'ja',
            'x-a-ise': 'False', 'x-a-isda': 'False', 'x-a-isop': 'False', 'x-a-isr': 'False',
            'x-a-s': 'adb9f0cb6bf3aa06f99cc15826dbbca7251f88369d38e1b4da5c5bc46ef3e951',
            'x-ad-id': '11ca2dbbd1d87224a04500e6ddfcc03f',
            'x-platform-user-id': '00000000-0000-0000-0000-000000000000', 'x-app-version': app_version}
    def close(self):
        self.channel.close()
    def call(self, service, method, request, response):
        self.headers['x-app-request-id'] = str(time.time_ns() // 100 + 621355968000000000)
        rpc = self.channel.unary_unary('/client.api.' + service + '/' + method,
            request_serializer=lambda obj: encode(obj.SerializeToString()),
            response_deserializer=lambda raw: message(self.pool, 'client.api.' + response).FromString(decode(raw)))
        try:
            return rpc(request, metadata=list(self.headers.items()), timeout=30)
        except grpc.RpcError as exc:
            # Details/metadata can contain credentials and signed URLs.
            raise RuntimeError(f'{service}/{method}: {exc.code().name}') from None
    def req(self, name='Empty', **kwargs):
        return message(self.pool, 'client.api.' + name, **kwargs)
    def login(self, credentials_path):
        credentials = json.loads(Path(credentials_path).read_text())
        token = firebase_request('https://securetoken.googleapis.com/v1/token',
            {'grantType': 'refresh_token', 'refreshToken': credentials['refresh_token']})
        credentials['refresh_token'] = token['refresh_token']
        save_credentials(credentials_path, credentials)
        self.call('System', 'Check', self.req('SystemCheckRequest'), 'SystemCheckResponse')
        self.call('System', 'Check', self.req('SystemCheckRequest', idToken=token['id_token']), 'SystemCheckResponse')
        login = self.call('Auth', 'Login', self.req('AuthLoginRequest', idToken=token['id_token']), 'AuthLoginResponse')
        if not login.gameAuthToken:
            raise RuntimeError('Game login did not return an auth token')
        self.headers['x-auth-token'] = login.gameAuthToken
        return login
    def manifest(self):
        result = self.call('Master', 'Get', self.req(), 'MasterGetResponse')
        if not result.masterTag.version or not result.masterTag.masterTagPacks:
            raise ValueError('Empty master manifest')
        return result
