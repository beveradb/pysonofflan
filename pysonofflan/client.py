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

    def __init__(self):
        self.basic_device_info = None
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

    async def connect(self, host: str, port: int = DEFAULT_PORT) -> None:
        """
        Connect to a Sonoff LAN Mode Device and set up handler for receiving messages.

        :param str host: host name or ip address of the device
        :param int port: port on the device (default: 8081)
        :return:
        """
        async with websockets.connect('ws://%s:%s' % host, port) as websocket:
            user_online_payload = self.get_user_online_payload()

            _LOGGER.debug('Sending user online websocket message: %s', json.dumps(user_online_payload))
            await websocket.send(user_online_payload)

            response = await websocket.recv()
            _LOGGER.debug('Received websocket response: %s', response)
            self.basic_device_info = json.loads(response)

            self.websocket = websocket

    async def send(self, request: Union[str, Dict]) -> Dict:
        """
        Send message to an already-connected Sonoff LAN Mode Device and return the response.

        :param request: command to send to the device (can be either dict or json string)
        :return:
        """
        if isinstance(request, dict):
            request = json.dumps(request)

        _LOGGER.debug('Sending websocket message: %s', json.dumps(request))

        await self.websocket.send(request)

        response = await self.websocket.recv()

        _LOGGER.debug('Received websocket response: %s', response)

        return json.loads(response)

    def get_basic_info(self):
        return self.basic_device_info
