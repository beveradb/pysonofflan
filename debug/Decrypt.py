import time
import requests
import json

from zeroconf import  ServiceBrowser, Zeroconf

from Crypto.Hash import MD5
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from base64 import b64decode

class SonoffR3:

    def __init__(self, Apikey):

        h = MD5.new()
        h.update(Apikey)
        self._key = h.digest()

    def Decrypt(self, encoded, iv):

        cipher = AES.new(self._key, AES.MODE_CBC, iv=b64decode(iv))
        ciphertext = b64decode(encoded)        
        padded = cipher.decrypt(ciphertext)
        plaintext = unpad(padded, AES.block_size)

        return plaintext

device = SonoffR3(b'key')
print(device.Decrypt(b'text', b'iv'))

