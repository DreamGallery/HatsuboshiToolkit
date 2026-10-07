"""Game qua transport; protocol reference: vertesan/campus (AGPL-3.0)."""
import gzip
import hashlib
import struct
import time
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

KEY = b'Kb31v85u'

def encode(data, ticks=None):
    if not data:
        return b''
    header = struct.pack('<Q', ticks if ticks is not None else time.time_ns() // 100 + 621355968000000000)
    cipher = AES.new(hashlib.md5(KEY).digest(), AES.MODE_CBC, hashlib.md5(KEY + header).digest())
    compressed = len(data) > 2048
    if compressed:
        data = gzip.compress(data, mtime=0)
    return bytes([10, 0, int(compressed), 8]) + header + cipher.encrypt(pad(data, 16))

def decode(raw):
    if not raw:
        return b''
    if len(raw) < 28 or raw[0] != raw[3] + 2 or raw[1] != 0 or raw[2] not in (0, 1):
        raise ValueError('Invalid qua header')
    end = 4 + raw[3]
    header, body = raw[4:end], raw[end:]
    if not body or len(body) % 16:
        raise ValueError('Invalid qua ciphertext length')
    cipher = AES.new(hashlib.md5(KEY).digest(), AES.MODE_CBC, hashlib.md5(KEY + header).digest())
    data = unpad(cipher.decrypt(body), 16)
    return gzip.decompress(data) if raw[2] else data
