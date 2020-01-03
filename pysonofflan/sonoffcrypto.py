""" Encrpytion routines as documented in https://github.com/itead/Sonoff_Devices_DIY_Tools/blob/master/other/SONOFF%20DIY%20MODE%20Protocol%20Doc.pdf
    
    Here are an abstract of the document with the partinent parts for the alogrithm
    
        The default password must be the API Key of the device. 
        
        The key used for encryption is the MD5 hash of the device password (16 bytes)
        
        The initialization vector iv used for encryption is a 16-byte random number, Base64 encoded as a string
        
        The encryption algorithm must be "AES-128-CBC/PKCS7Padding" (AES 128 Cipher Block Chaining (CBC) with PKCS7 Padding)
        
        When the device information (unencrypted or encrypted string) is longer than 249 bytes, the first 249 bytes must be stored in data1, and the remaining bytes are divided by length 249, which are stored in data2, data3, and data4.
        
        [This last part is currently unimplemented as I haven't seen a mesage longer than 249 bytes as yet, proably will have on multi-channel devices]
        
        
"""

from Crypto.Hash import MD5
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad, pad
from base64 import b64decode, b64encode
from Crypto.Random import get_random_bytes
import json

def format_encryption_msg(payload, api_key, data):

    payload["selfApikey"] = "cb0ff096-2a9d-4250-93ec-362fc1fe6f40" # This field needs to exist, but no idea what it is used for (https://github.com/itead/Sonoff_Devices_DIY_Tools/issues/5)
    iv = generate_iv()
    payload["iv"] = b64encode(iv).decode("utf-8") 
    payload["encrypt"] = True
 
    if data is None:
        # data["data"] = encrypt("{ }", iv)
        payload["data"] = ""
    else:
        payload["data"] = encrypt(json.dumps(data, separators = (',', ':') ), iv, api_key)


def format_encryption_txt(properties, data, api_key):

    properties["encrypt"] = True

    iv = generate_iv()
    properties["iv"] = b64encode(iv).decode("utf-8") 

    return encrypt(data, iv, api_key)


def encrypt(data_element, iv, api_key):

    api_key = bytes(api_key, 'utf-8') 
    plaintext = bytes(data_element, 'utf-8')

    hash = MD5.new()
    hash.update(api_key)
    key = hash.digest()

    cipher = AES.new(key, AES.MODE_CBC, iv=iv)     
    padded = pad(plaintext, AES.block_size)
    ciphertext = cipher.encrypt(padded)
    encoded = b64encode(ciphertext) 

    return encoded.decode("utf-8")


def decrypt(data_element, iv, api_key):

    api_key = bytes(api_key, 'utf-8')
    encoded =  data_element

    hash = MD5.new()
    hash.update(api_key)
    key = hash.digest()

    cipher = AES.new(key, AES.MODE_CBC, iv=b64decode(iv))
    ciphertext = b64decode(encoded)        
    padded = cipher.decrypt(ciphertext)
    plaintext = unpad(padded, AES.block_size)
    
    return plaintext


def generate_iv():
    return get_random_bytes(16)