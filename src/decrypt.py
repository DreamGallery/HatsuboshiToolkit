import proto.octodb_pb2 as octop
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from src.config import API_KEY


def decrypt_database_from_api(enc_data: bytes, key: bytes = API_KEY, offset: int = 16) -> octop.Database:
    iv = enc_data[:offset]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    dec_data = unpad(cipher.decrypt(enc_data[offset:]), block_size=16, style="pkcs7")
    database = octop.Database.FromString(dec_data)
    return database


def string_to_mask_bytes(mask_string: str, mask_string_length: int, bytes_length: int) -> bytes:
    mask_bytes = bytearray(bytes_length)
    if mask_string != 0:
        if mask_string_length >= 1:
            i = 0
            j = 0
            k = bytes_length - 1
            while mask_string_length != j:
                char_j = mask_string[j]
                # must be casted as Int in python
                char_j = int.from_bytes(char_j.encode("ascii"), byteorder="little", signed=False)
                j += 1
                mask_bytes[i] = char_j
                i += 2
                # must add &0xFF to get a unsigned integer in python otherwise it will return the signed one
                char_j = ~char_j & 0xFF
                # .to_bytes(length=1, byteorder="little", signed=True)
                mask_bytes[k] = char_j
                k -= 2
        if bytes_length >= 1:
            l = bytes_length
            v13 = 0x9B
            m = bytes_length
            pointer = 0
            while m:
                v16 = mask_bytes[pointer]
                pointer += 1
                m -= 1
                v13 = (((v13 & 1) << 7) | (v13 >> 1)) ^ v16
            b = 0
            while l:
                l -= 1
                mask_bytes[b] ^= v13
                b += 1
    return bytes(mask_bytes)


def crypt_by_string(
    input: bytes, mask_string: str, offset: int, stream_pos: int, header_length: int
) -> bytes:
    mask_string_length = mask_string.__len__()
    bytes_length = mask_string_length << 1
    buffer = bytearray(input)
    mask_bytes = string_to_mask_bytes(mask_string, mask_string_length, bytes_length)
    i = 0
    while stream_pos + i < header_length:
        buffer[offset + i] ^= mask_bytes[stream_pos + i - int((stream_pos + i) / bytes_length) * bytes_length]
        i += 1
    return bytes(buffer)
