import binascii
import json
import logging
import random
import time
from typing import Dict, Union, Callable, Awaitable
import asyncio
import threading
import enum
import traceback

import requests
from zeroconf import  ServiceBrowser, Zeroconf

from Crypto.Hash import MD5
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad, pad
from base64 import b64decode, b64encode
from Crypto.Random import get_random_bytes

class SonoffLANModeClient:
    """
    Implementation of the Sonoff LAN Mode Protocol R3(as used by the eWeLink app)
    """

    """
    Initialise class with connection parameters

    :param str host: host name (ip address is not supported) as hostname is the mDS servie name
    :return:
    """

    DEFAULT_PORT = 8081
    DEFAULT_TIMEOUT = 5
    DEFAULT_PING_INTERVAL = 5

    def __init__(self, host: str,
                 event_handler: Callable[[str], Awaitable[None]],
                 ping_interval: int = DEFAULT_PING_INTERVAL,
                 timeout: int = DEFAULT_TIMEOUT,
                 logger: logging.Logger = None):

        self.host = host
        self.logger = logger
        self.event_handler = event_handler
        self.connected_event = asyncio.Event()
        self.disconnected_event = asyncio.Event()
        # self.message_received_event = asyncio.Event()
        self.browser = None
        self.zeroconf = Zeroconf()
        self.loop = None

        self.session = None

        if self.logger is None:
            self.logger = logging.getLogger(__name__)

    async def connect(self):
        """
        Setup a mDNS listener
        """

        # service_name = "eWeLink_" + self.host + "._ewelink._tcp.local."
        service_name = "_ewelink._tcp.local."

        self.logger.debug('Listening for service to %s', service_name)

        self.browser = ServiceBrowser(self.zeroconf, service_name, listener=self)

    async def close_connection(self):

        self.browser = None

    
   
    def remove_service(self, zeroconf, type, name):
        self.logger.warn("Service %s removed" % name)

        # self.shutdown_event_loop()

    def add_service(self, zeroconf, type, name):

        self.logger.debug("Service %s added" % name)

        wanted_service_name = "eWeLink_" + self.host + "._ewelink._tcp.local."

        if name == wanted_service_name:
            self.update_service(zeroconf, type, name)
            
            # listen for updates too
            self.browser = ServiceBrowser(self.zeroconf, name, listener=self)

            # create an http session 
            self.session = requests.Session()

            # add the headers       
            headers = { 'Content-Type': 'application/json;charset=UTF-8',
                'Accept': 'application/json',
                'Accept-Language': 'en-gb'        
            }    
            self.session.headers.update(headers)

            # find and store the URL
            info = zeroconf.get_service_info(type, name)
            socket = self.parseAddress(info.address) + ":" + str(info.port)
            self.logger.debug("service is at %s", socket)
            self.url = 'http://' + socket + '/zeroconf/switch'
            self.logger.debug("url for switch is %s", self.url)

    def update_service(self, zeroconf, type, name):


        info = zeroconf.get_service_info(type, name)

        self.logger.debug("Service %s updated" % name)
        self.logger.debug("properties: %s",info.properties)

        iv = info.properties.get(b'iv')
        data1 = info.properties.get(b'data1')

        plaintext = self.decrypt(data1,iv)

        self.data = plaintext

        self.logger.debug("data: %s", plaintext)

        asyncio.run_coroutine_threadsafe(self.event_handler(self.data), self.loop)

        self.logger.debug('exiting update_service')

    async def receive_message_loop(self):

        self.loop = asyncio.get_running_loop()

        """try:
            while True:
                self.logger.debug('Waiting for messages')

                self.message_received_event.wait()
                
                self.logger.debug('Message received')
                await self.event_handler(self.data)
                self.message_received_event.clear()
                self.logger.debug('Message passed to handler, should loop now')
        except Exception as ex:
            self.logger.error('Unexpected error in receive_message_loop(): %s %s', format(ex), traceback.format_exc() )       

        finally:
            self.logger.debug('receive_message_loop finally block reached: ')"""

    async def send(self, request: Union[str, Dict]):
        """
        Send message to an already-connected Sonoff LAN Mode Device
        and return the response.

        :param request: command to send to the device (can be dict or json)
        :return:
        """

        self.logger.debug('Sending http message: %s', request)      
        response = self.session.post(self.url, json=request)
        self.logger.debug('response received: %s %s', response, response.content) 

        response_json = json.loads(response.content)

        if response_json['error'] != 0:
            self.logger.warn('error received: %s', response.content)                  
        else:
            self.logger.info('message sent to switch successfully') 

    def get_update_payload(self, device_id: str, params: dict) -> Dict:

        try:
            payload = {
                'sequence': str(int(time.time())), # ensure this field isn't too long, otherwise buffer overflow type issue caused in the device
                'deviceid': device_id,
                #'selfApikey': 'cb0ff096-2a9d-4250-93ec-362fc1fe6f40',  # No apikey needed in LAN mode
                'selfApikey': '123',  # This field need to exist, but no idea what it is used for (https://github.com/itead/Sonoff_Devices_DIY_Tools/issues/5)
                'data': json.dumps(params)
            }

            self.logger.debug('message to send (plaintext): %s', payload)             

            self.format_encryption(payload)

        except Exception as ex:
            self.logger.error('Unexpected error in send(): %s %s', format(ex), traceback.format_exc() )


        return payload

    def format_encryption(self, data):

        encrypt = True
        data["encrypt"] = encrypt
        if encrypt:
            iv = self.generate_iv()
            data["iv"] = b64encode(iv).decode("utf-8") 
            data["data"] = self.encrypt(data["data"], iv)

    def encrypt(self, data_element, iv):

        ApiKey = b'3c1433d8-a02c-479a-a126-ac9438e6bfe5' # [INSERT_TEST_API_KEY_HERE]
        plaintext = bytes(data_element, 'utf-8')

        h = MD5.new()
        h.update(ApiKey)
        key = h.digest()

        cipher = AES.new(key, AES.MODE_CBC, iv=iv)     
        padded = pad(plaintext, AES.block_size)
        ciphertext = cipher.encrypt(padded)
        encode = b64encode(ciphertext) 

        print(encode)
        return encode.decode("utf-8")

    def generate_iv(self):
        return get_random_bytes(16)

    def decrypt(self, data_element, iv):

        ApiKey = b'3c1433d8-a02c-479a-a126-ac9438e6bfe5' # [INSERT_TEST_API_KEY_HERE]
        encoded =  data_element

        h = MD5.new()
        h.update(ApiKey)
        key = h.digest()

        cipher = AES.new(key, AES.MODE_CBC, iv=b64decode(iv))
        ciphertext = b64decode(encoded)        
        padded = cipher.decrypt(ciphertext)
        plaintext = unpad(padded, AES.block_size)

        return plaintext

    def parseAddress(self, address):
        """
        Resolve the IP address of the device
        :param address:
        :return: add_str
        """
        add_list = []
        for i in range(4):
            add_list.append(int(address.hex()[(i * 2):(i + 1) * 2], 16))
        add_str = str(add_list[0]) + "." + str(add_list[1]) + \
            "." + str(add_list[2]) + "." + str(add_list[3])
        return add_str
