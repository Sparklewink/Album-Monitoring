
import base64
import binascii
import json
import os
from Crypto.Cipher import AES
MODULUS = (
    "00e0b509f6259df8642dbc35662901477df22677ec152b5ff68ace615bb7"
    "b725152b3ab17a876aea8a5aa76d2e417629ec4ee341f56135fccf695280"
    "104e0312ecbda92557c93870114af6c9d05c4f7f0c3685b7a46bee255932"
    "575cce10b424d813cfe4875d3e82047b97ddef52741d546b8e289dc6935b"
    "3ece0462db0a22b8e7"
)
NONCE = b"0CoJUm6Qyw8W8jud"
PUBKEY = "010001"
# ----------------------------------------------------

def _aes_encrypt(text, key):
    """AES加密"""
    pad = 16 - len(text) % 16
    text = text + bytearray([pad] * pad)
    encryptor = AES.new(key, 2, b"0102030405060708")
    ciphertext = encryptor.encrypt(text)
    return base64.b64encode(ciphertext)

def _rsa_encrypt(text, pubkey, modulus):
    """RSA加密"""
    text = text[::-1]
    rs = pow(
        int(binascii.hexlify(text), 16),
        int(pubkey, 16),
        int(modulus, 16),
    )
    return format(rs, "x").zfill(256)

def encrypted_request(data):
    """
    主函数：传入原始POST数据，返回加密后的数据
    """
    data = json.dumps(data).encode("utf-8")
    secret_key = os.urandom(16)
    secret_key = binascii.hexlify(secret_key)[:16]
    
    params = _aes_encrypt(data, NONCE)
    params = _aes_encrypt(params, secret_key)
    
    enc_seckey = _rsa_encrypt(secret_key, PUBKEY, MODULUS)
    
    return {"params": params.decode("utf-8"), "encSecKey": enc_seckey}