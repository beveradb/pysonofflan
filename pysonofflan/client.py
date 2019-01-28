import json
import logging
import random
import time
from typing import Dict, Union

import websockets

_LOGGER = logging.getLogger(__name__)


class SonoffLANModeClient:
    """
    Implementation of the Sonoff LAN Mode Protocol (as used by the eWeLink app)
    """
    DEFAULT_PORT = 8081
    DEFAULT_TIMEOUT = 5

    """
    Initialise class with connection parameters

    :param str host: host name or ip address of the device
    :param int port: port on the device (default: 8081)
    :return:
    """

    def __init__(self, host: str, port: int = DEFAULT_PORT):
        self.host = host
        self.port = port
        self.basic_device_info = {}
        self.latest_params = {}
        self.websocket = None

    @staticmethod
    def get_user_online_payload() -> Dict:
        return {
            'action': "userOnline",
            'userAgent': 'app',
            'version': 6,
            'nonce': ''.join([str(random.randint(0, 9)) for i in range(15)]),
            'apkVesrion': "1.8",
            'os': 'ios',
            'at': 'at',  # No bearer token needed in LAN mode
            'apikey': 'apikey',  # No apikey needed in LAN mode
            'ts': str(int(time.time())),
            'model': 'iPhone10,6',
            'romVersion': '11.1.2',
            'sequence': str(time.time()).replace('.', '')
        }

    @staticmethod
    def get_update_payload(device_id: str, params: dict) -> Dict:
        return {
            'action': 'update',
            'userAgent': 'app',
            'params': params,
            'apikey': 'apikey',  # No apikey needed in LAN mode
            'deviceid': device_id,
            'sequence': str(time.time()).replace('.', ''),
            'controlType': 4,
            'ts': 0
        }

    async def connect(self) -> None:
        """
        Connect to the Sonoff LAN Mode Device and set up handler for receiving messages.
        :return:
        """
        websocket_address = 'ws://%s:%s/' % (self.host, self.port)
        _LOGGER.debug('Connecting to websocket address: %s', websocket_address)

        async with websockets.connect(websocket_address) as websocket:
            self.websocket = websocket
            response = self.send(self.get_user_online_payload())
            self.basic_device_info = json.loads(response)

    async def send(self, request: Union[str, Dict]) -> Dict:
        """
        Send message to an already-connected Sonoff LAN Mode Device and return the response.

        :param request: command to send to the device (can be either dict or json string)
        :return:
        """
        if self.websocket is None:
            await self.connect()

        if isinstance(request, dict):
            request = json.dumps(request)

        _LOGGER.debug('Sending websocket message: %s', json.dumps(request))
        await self.websocket.send(request)

        response = await self.websocket.recv()
        _LOGGER.debug('Received websocket response: %s', response)

        response_data = json.loads(response)

        if 'params' in response_data:
            self.latest_params = response_data.params

        return response_data

    async def get_basic_info(self) -> Dict:
        if self.websocket is None:
            await self.connect()

        return self.basic_device_info

    async def get_latest_params(self) -> Dict:
        if self.websocket is None:
            await self.connect()

        return self.latest_params
