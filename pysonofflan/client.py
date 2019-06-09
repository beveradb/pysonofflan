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
from zeroconf import ServiceBrowser, Zeroconf

from Crypto.Hash import MD5
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad, pad
from base64 import b64decode, b64encode
from Crypto.Random import get_random_bytes

import socket

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

    zeroconf = Zeroconf()

    def __init__(self, host: str,
                 event_handler: Callable[[str], Awaitable[None]],
                 ping_interval: int = DEFAULT_PING_INTERVAL,
                 timeout: int = DEFAULT_TIMEOUT,
                 logger: logging.Logger = None,
                 loop = None,
                 device_id: str = "",
                 api_key: str = ""):

        self.host = host
        self.device_id = device_id
        self.api_key = api_key
        self.logger = logger
        self.event_handler = event_handler
        self.connected_event = asyncio.Event()
        self.disconnected_event = asyncio.Event()
        self.service_browser = None
        self.loop = loop
        self.http_session = None
        self.my_service_name = None
        self.last_request = None

        if self.logger is None:
            self.logger = logging.getLogger(__name__)

    def connect(self):
        """
        Setup a mDNS listener
        """

        # listen for any added SOnOff
        self.service_browser = ServiceBrowser(SonoffLANModeClient.zeroconf, SonoffLANModeClient.SERVICE_TYPE, listener=self)

    def close_connection(self):

        self.logger.debug("enter close_connection()")
        self.service_browser = None
        self.disconnected_event.set()
        self.my_service_name = None

    def remove_service(self, zeroconf, type, name):

        if self.my_service_name == name:

            # hack! send a wake-up message to the switch to see if its still there
            if self.send_signal_strength(self.get_update_payload(self.device_id, None)) != 0:
                self.logger.warn("Service %s removed" % name)
                self.close_connection()
            
            self.logger.debug("Service %s removed (but hack worked)" % name)

        #else:
        #    self.logger.debug("Service %s removed (not our switch)" % name)

    def add_service(self, zeroconf, type, name):

        if self.my_service_name is not None:
        
            if self.my_service_name == name:
                self.logger.debug("Service %s added (again, likely after hack)" % name)
                self.my_service_name = None

            #else:
            #    self.logger.debug("Service %s added (not our switch)" % name)

        if self.my_service_name is None:
        
            info = zeroconf.get_service_info(type, name)
            found_ip = self.parseAddress(info.address)

            if self.device_id is not None:

                if name == "eWeLink_" + self.device_id + "." + SonoffLANModeClient.SERVICE_TYPE:
                    self.my_service_name = name

            elif self.host is not None:

                try:

                    if socket.gethostbyname(self.host) == found_ip:
                        self.my_service_name = name

                except TypeError:

                    if self.host == found_ip:
                        self.my_service_name = name

            if self.my_service_name is not None:

                self.logger.info("Service type %s of name %s added", type, name) 

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

                # find socket for end-point
                socket_text = found_ip + ":" + str(info.port)          
                self.logger.debug("service is at %s", socket_text)
                self.url = 'http://' + socket_text

                # setup retries (https://urllib3.readthedocs.io/en/latest/reference/urllib3.util.html#urllib3.util.retry.Retry)
                from requests.adapters import HTTPAdapter
                from urllib3.util.retry import Retry

                # no retries at moment using requests class, control in sonoffdevice (review after seeing what failure we get)
                retries = Retry(total=0, backoff_factor=0.5, method_whitelist=['POST'], status_forcelist=None)
                self.http_session.mount('http://', HTTPAdapter(max_retries=retries))

                # process the initial message
                self.update_service(zeroconf, type, name)


    def update_service(self, zeroconf, type, name):

        info = zeroconf.get_service_info(type, name)
        self.logger.debug("properties: %s",info.properties)

        if info.properties.get(b'encrypt'):
            # decrypt the message
            iv = info.properties.get(b'iv')
            data1 = info.properties.get(b'data1')
            plaintext = self.decrypt(data1,iv)
            data = plaintext
            self.logger.debug("decrypted data: %s", plaintext)

        else:
            data = info.properties.get(b'data1')

        self.properties = info.properties

        # process the events on an event loop (this method is on a background thread called from zeroconf)
        asyncio.run_coroutine_threadsafe(self.event_handler(data), self.loop)


    def send_switch(self, request: Union[str, Dict]):

        try:
            return self.send(request, self.url + '/zeroconf/switch')

        except Exception as ex:
            self.logger.error('Unexpected error in send_switch(): %s %s', format(ex), traceback.format_exc)

    def send_signal_strength(self, request: Union[str, Dict]):

        return self.send(request, self.url + '/zeroconf/signal_strength')

    def send(self, request: Union[str, Dict], url):
        """
        Send message to an already-connected Sonoff LAN Mode Device
        and return the response.
        :param request: command to send to the device (can be dict or json)
        :return:
        """

        try:

            self.logger.debug('Sending http message to %s: %s ', url, request)      
            response = self.http_session.post(url, json=request)
            self.logger.debug('response received: %s %s', response, response.content) 

            response_json = json.loads(response.content)

            error = response_json['error']

            if error != 0:
                self.logger.warn('error received: %s', response.content)
                # no need to process error, retry will resend message which should be sufficient

            else:
                self.logger.debug('message sent to switch successfully') 
                # no need to do anything here, the update is processed via the mDNS TXT record update

            return error

        except Exception as ex:
            self.logger.error('Unexpected error in send(): %s %s', format(ex), traceback.format_exc)


    def get_update_payload(self, device_id: str, params: dict) -> Dict:

        payload = {
            'sequence': str(int(time.time())), # ensure this field isn't too long, otherwise buffer overflow type issue caused in the device
            'deviceid': device_id,
            'selfApikey': '123',  # This field need to exist, but no idea what it is used for (https://github.com/itead/Sonoff_Devices_DIY_Tools/issues/5)
            'data': json.dumps(params)
        }

        self.logger.debug('message to send (plaintext): %s', payload)

        if self.api_key != "":
            self.format_encryption(payload)
            self.logger.debug('encrypted: %s', payload)

        return payload

    def format_encryption(self, data):

        encrypt = True
        data["encrypt"] = encrypt
        if encrypt:
            iv = self.generate_iv()
            data["iv"] = b64encode(iv).decode("utf-8") 
            data["data"] = self.encrypt(data["data"], iv)

    def encrypt(self, data_element, iv):

        ApiKey = bytes(self.api_key, 'utf-8') 
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

        ApiKey = bytes(self.api_key, 'utf-8')
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
