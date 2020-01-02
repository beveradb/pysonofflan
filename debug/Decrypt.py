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

device = SonoffR3(b'b5b46dce-d365-4f2e-b507-b09269c4ddb6')
print(device.Decrypt(b'oCKuglULSEok8/xaS8ZMS9HPjpK/0WYgFrzaSnTnJSpbmKz2NCIee7Mhzvf9GU+/', b'"MDQ2OTgyMTAyMjcxODU3Ng=="'))

device = SonoffR3(b'b5b46dce-d365-4f2e-b507-b09269c4ddb6')
print(device.Decrypt(b'2BqVsSYoQxFP43zTKxZfc1i2CYDhTX6pYp4tGySiczMDnpYAb6/UTGhKt3kbhm+P', b'HwQWNfMgpBRjODqTUcH1+A=='))


