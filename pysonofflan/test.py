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

        self.selfApikey = b'cb0ff096-2a9d-4250-93ec-362fc1fe6f40'

        h = MD5.new()
        h.update(Apikey)
        self._key = h.digest()

    def Decrypt(self, encoded, iv):

        cipher = AES.new(self._key, AES.MODE_CBC, iv=b64decode(iv))
        ciphertext = b64decode(encoded)        
        padded = cipher.decrypt(ciphertext)
        plaintext = unpad(padded, AES.block_size)

        return plaintext

    def TurnOn(self):

        headers = { 'Content-Type': 'application/json;charset=UTF-8',
            'Accept': 'application/json',
            'Accept-Language': 'en-gb'        
        }           

        url = 'http://192.168.0.227:8081/zeroconf/switch'

        payload = {"sequence": str(time.time()).replace('.','',1), 'deviceid': '100065a6b1',
            "selfApikey":'cb0ff096-2a9d-4250-93ec-362fc1fe6f40',
            "iv": b'Mjk4ODI2MjQ3Mjg3NTMwOA==',
            "encrypt": True,
            "data": b'kJpLhTrx2TNyllFbrjYdKg=='}

        print(payload)

        r = requests.post(url, headers=headers, json=payload)
        print(r.content)

"""

Not working

http://192.168.0.227:8081/zeroconf/switch 
{'sequence': '1557476936', 'deviceid': '100065a6b1', 
'encrypt': True, 'iv': b'MTIzNDU2Nzg5MDEyMzQ1Ng==', 
'selfApikey': '123', 
'data': b'V+P0LafLxBVADYns4TzF1xAQEBAQEBAQEBAQEBAQEBA='}
"""

class MyListener:

    info = None

    def remove_service(self, zeroconf, type, name):
        print("Service %s removed" % (name,))

    def add_service(self, zeroconf, type, name):

        print("Service %s added" % name)

        self.update_service(zeroconf, type, name)

        ServiceBrowser(zeroconf, name, listener)

    def update_service(self, zeroconf, type, name):

        self.info = zeroconf.get_service_info(type, name)

        iv = self.info.properties.get(b'iv')
        data1 = self.info.properties.get(b'data1')
        device = SonoffR3(b'3c1433d8-a02c-479a-a126-ac9438e6bfe5')
        plaintext = device.Decrypt(data1,iv)
        print(plaintext)
        

zeroconf = Zeroconf()
listener = MyListener()
browser = ServiceBrowser(zeroconf, "_ewelink._tcp.local.", listener)

try:
    input("Press enter to send...\n\n")

    device = SonoffR3(b'3c1433d8-a02c-479a-a126-ac9438e6bfe5')
    device.TurnOn()

finally:
    zeroconf.close()



