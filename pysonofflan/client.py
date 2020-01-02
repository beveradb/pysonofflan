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
import collections
import requests
from zeroconf import ServiceBrowser, Zeroconf

from . import sonoffcrypto
import socket

class SonoffLANModeClient:
    """
    Implementation of the Sonoff LAN Mode Protocol R3(as used by the eWeLink app)
    
    Uses protocol as documented here by Itead https://github.com/itead/Sonoff_Devices_DIY_Tools/blob/master/other/SONOFF%20DIY%20MODE%20Protocol%20Doc.pdf
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
                 api_key: str = "",
                 outlet: int = None):

        self.host = host
        self.device_id = device_id
        self.api_key = api_key
        self.outlet = outlet
        self.logger = logger
        self.event_handler = event_handler
        self.connected_event = asyncio.Event()
        self.disconnected_event = asyncio.Event()
        self.service_browser = None
        self.loop = loop
        self.http_session = None
        self.my_service_name = None
        self.last_request = None
        self.encrypted = False
        self.type = None

        self._last_params= {"switch": "off"}

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
            self.logger.debug("Service %s flagged for removal" % name)
            self.loop.run_in_executor(None, self.retry_connection )


    def add_service(self, zeroconf, type, name):

        if self.my_service_name is not None:
        
            if self.my_service_name == name:
                self.logger.debug("Service %s added (again)" % name)
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
                headers = collections.OrderedDict( { 'Content-Type': 'application/json;charset=UTF-8',
                    'User-Agent': 'ewelinkDemo/2 CFNetwork/1121.2.2 Darwin/19.2.0',
                    'Connection': 'keep-alive',
                    'Accept': 'application/json',
                    'Accept-Language': 'en-gb',
                    'Content-Length': "0",
                    'Accept-Encoding': 'gzip, deflate',
                    'Cache-Control': 'no-store'        
                } )

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

        try:
            info = zeroconf.get_service_info(type, name)
            self.logger.debug("properties: %s",info.properties)

            self.type = info.properties.get(b'type')
            self.logger.debug("type: %s", self.type)

            data1 = info.properties.get(b'data1')
            data2 = info.properties.get(b'data2')

            if data2 is not None:
                data1 += data2
                data3 = info.properties.get(b'data3')

                if data3 is not None:              
                    data1 += data3
                    data4 = info.properties.get(b'data4')

                    if data4 is not None:
                        data1 += data4

            if info.properties.get(b'encrypt'):
                self.encrypted = True
                # decrypt the message
                iv = info.properties.get(b'iv')
                data = sonoffcrypto.decrypt(data1,iv, self.api_key)
                self.logger.debug("decrypted data: %s", data)

            else:
                self.encrypted = False
                data = data1

            self.properties = info.properties

            # process the events on an event loop (this method is on a background thread called from zeroconf)
            asyncio.run_coroutine_threadsafe(self.event_handler(data), self.loop)

        except Exception as ex:
            self.logger.error('Error updating service for device %s: %s, probably wrong API key', self.device_id, format(ex)) 


    def retry_connection(self):

        while True:
            try:
                self.logger.debug("Sending retry message for %s" % self.device_id)
                self.send_signal_strength()
                self.logger.info("Service %s not removed (hack worked)" % self.device_id)
                break

            except OSError as ex:
                self.logger.debug('Connection issue for device %s: %s', self.device_id, format(ex))
                self.logger.warn("Service %s removed" % self.device_id)
                self.close_connection()
                break

            except Exception as ex:
                self.logger.error('Retry_connection() Unexpected error for device %s: %s %s', self.device_id, format(ex), traceback.format_exc)
                break


    def send_switch(self, request: Union[str, Dict]):

        response = self.send(request, self.url + '/zeroconf/switch')

        try:
            response_json = json.loads(response.content)

            error = response_json['error']

            if error != 0:
                self.logger.warn('error received: %s, %s', self.device_id, response.content)
                # no need to process error, retry will resend message which should be sufficient

            else:
                self.logger.debug('message sent to switch successfully') 
                # no need to do anything here, the update is processed via the mDNS TXT record update

            return response

        except:
            self.logger.error('error processing response: %s, %s', response, response.content)

        finally:

            return

    def send_signal_strength(self):

        return self.send(self.get_update_payload(self.device_id, {} ), self.url + '/zeroconf/signal_strength')


    def send_info(self, request: Union[str, Dict]):

        return self.send(self.get_update_payload(self.device_id, {} ), self.url + '/zeroconf/info')


    def send(self, request: Union[str, Dict], url):
        """
        Send message to an already-connected Sonoff LAN Mode Device
        and return the response.
        :param request: command to send to the device (can be dict or json)
        :return:
        """
        
        data = json.dumps(request,  separators = (',', ':'))
        self.logger.debug('Sending http message to %s: %s', url, data)      
        response = self.http_session.post(url, data=data)
        self.logger.debug('response received: %s %s', response, response.content) 

        return response

    def get_update_payload(self, device_id: str, params: dict) -> Dict:

        self._last_params = params

        ''' Hack for multi outlet switches, needs improving '''
        if self.type == b'strip':

            if self.outlet is None:
                self.outlet = 0

            switches = {"switches":[{"switch":"off","outlet":0}]}
            switches["switches"][0]["switch"] = params["switch"]
            switches["switches"][0]["outlet"] = int(self.outlet)
            params = switches


        payload = {
            "sequence": str(int(time.time()*1000)), # ensure this field isn't too long, otherwise buffer overflow type issue caused in the device
            "deviceid": device_id,
            }


        if self.encrypted:

            self.logger.debug('params: %s', params)

            if self.api_key != "" and self.api_key is not None:
                sonoffcrypto.format_encryption_msg(payload, self.api_key, params)
                self.logger.debug('encrypted: %s', payload)

            else:
                self.logger.error('missing api_key field for device: %s', self.device_id) 

        else:
            payload["encrypt"] = False
            payload["data"] = params
            self.logger.debug('message to send (plaintext): %s', payload)

        return payload

        



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
