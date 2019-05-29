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

    DEFAULT_TIMEOUT = 5
    DEFAULT_PING_INTERVAL = 5
    SERVICE_TYPE = "_ewelink._tcp.local."

    def __init__(self, host: str,
                 event_handler: Callable[[str], Awaitable[None]],
                 ping_interval: int = DEFAULT_PING_INTERVAL,
                 timeout: int = DEFAULT_TIMEOUT,
                 logger: logging.Logger = None,
                 loop = None,
                 api_key: str = None):

        self.host = host
        self.api_key = api_key
        self.logger = logger
        self.event_handler = event_handler
        self.connected_event = asyncio.Event()
        self.disconnected_event = asyncio.Event()
        self.service_browser = None
        self.zeroconf = Zeroconf()
        self.loop = loop
        self.http_session = None
        self.my_service_name = "eWeLink_" + self.host + "." + SonoffLANModeClient.SERVICE_TYPE


        if self.logger is None:
            self.logger = logging.getLogger(__name__)

    def connect(self):
        """
        Setup a mDNS listener
        """

        # listen for any added SOnOff
        self.logger.debug('Listening for service to %s', SonoffLANModeClient.SERVICE_TYPE)
        self.service_browser = ServiceBrowser(self.zeroconf, SonoffLANModeClient.SERVICE_TYPE, listener=self)

    async def close_connection(self):

        self.logger.debug("Connection closed called")
        self.service_browser = None
        self.disconnected_event.set()
        self.connected_event.clear()

    def remove_service(self, zeroconf, type, name):

        self.logger.warn("Service %s removed" % name)
        self.disconnected_event.set()
        self.cconnected_event.clear()

    def add_service(self, zeroconf, type, name):

        if name == self.my_service_name:

            self.logger.debug("Service type %s of name %s added", type, name) 

            # listen for updates to the specific device
            self.service_browser = ServiceBrowser(zeroconf, name, listener=self)

            # create an http session so we can use http keep-alives
            self.http_session = requests.Session()

            # add the http headers
            headers = { 'Content-Type': 'application/json;charset=UTF-8',
                'Accept': 'application/json',
                'Accept-Language': 'en-gb'        
            }    
            self.http_session.headers.update(headers)

            # find and store the URL to be used in send()
            info = zeroconf.get_service_info(type, name)
            self.logger.warn("ServiceInfo: %s", info)
            socket = self.parseAddress(info.address) + ":" + str(info.port)
            self.logger.debug("service is at %s", socket)
            self.url = 'http://' + socket + '/zeroconf/switch'
            self.logger.debug("url for switch is %s", self.url)

            # process the initial message
            self.update_service(zeroconf, type, name)
           
    def update_service(self, zeroconf, type, name):

        self.logger.debug("Service %s updated" % name)
        info = zeroconf.get_service_info(type, name)
        self.logger.debug("properties: %s",info.properties)

        # decrypt the message
        iv = info.properties.get(b'iv')
        data1 = info.properties.get(b'data1')
        plaintext = self.decrypt(data1,iv)
        self.data = plaintext
        self.logger.debug("data: %s", plaintext)

        # process the events on an event loop (this method is on a background thread called from zeroconf)
        asyncio.run_coroutine_threadsafe(self.event_handler(self.data), self.loop)

        self.logger.debug('exiting update_service')

    async def send(self, request: Union[str, Dict]):
        """
        Send message to an already-connected Sonoff LAN Mode Device
        and return the response.
        :param request: command to send to the device (can be dict or json)
        :return:
        """

        self.logger.debug('Sending http message: %s', request)      
        response = self.http_session.post(self.url, json=request)
        self.logger.debug('response received: %s %s', response, response.content) 

        response_json = json.loads(response.content)

        if response_json['error'] != 0:
            self.logger.warn('error received: %s', response.content)
            # todo: think about how to process errors, or if retry in calling routine is sufficient
        else:
            self.logger.debug('message sent to switch successfully') 
            # no need to do anything here, the update is processed via the mDNS TXT record update
            
    def get_update_payload(self, device_id: str, params: dict) -> Dict:

        payload = {
            'sequence': str(int(time.time())), # ensure this field isn't too long, otherwise buffer overflow type issue caused in the device
            'deviceid': device_id,
            #'selfApikey': 'cb0ff096-2a9d-4250-93ec-362fc1fe6f40',  # No apikey needed in LAN mode
            'selfApikey': '123',  # This field need to exist, but no idea what it is used for (https://github.com/itead/Sonoff_Devices_DIY_Tools/issues/5)
            'data': json.dumps(params)
        }

        self.logger.debug('message to send (plaintext): %s', payload)             
        self.format_encryption(payload)
        return payload

    def format_encryption(self, data):

        encrypt = True
        data["encrypt"] = encrypt
        if encrypt:
            iv = self.generate_iv()
            data["iv"] = b64encode(iv).decode("utf-8") 
            data["data"] = self.encrypt(data["data"], iv)

    def encrypt(self, data_element, iv):

        ApiKey = bytes(self.api_key, 'utf-8') # b'3c1433d8-a02c-479a-a126-ac9438e6bfe5' # [INSERT_TEST_API_KEY_HERE]
        plaintext = bytes(data_element, 'utf-8')

        h = MD5.new()
        h.update(ApiKey)
        key = h.digest()

        cipher = AES.new(key, AES.MODE_CBC, iv=iv)     
        padded = pad(plaintext, AES.block_size)
        ciphertext = cipher.encrypt(padded)
        encode = b64encode(ciphertext) 

        return encode.decode("utf-8")

    def generate_iv(self):
        return get_random_bytes(16)

    def decrypt(self, data_element, iv):

        self.logger.debug('decrypt() entry: %s', self.api_key)

        ApiKey = bytes(self.api_key, 'utf-8') # b'3c1433d8-a02c-479a-a126-ac9438e6bfe5' # [INSERT_TEST_API_KEY_HERE]
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
