import asyncio
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
    DEFAULT_TIMEOUT = 20

    """
    Initialise class with connection parameters

    :param str host: host name or ip address of the device
    :param int port: port on the device (default: 8081)
    :return:
    """

    def __init__(self, host: str, port: int = DEFAULT_PORT):
        self.host = host
        self.port = port
        self.websocket = None

    @asyncio.coroutine
    def connect(self, event_handler) -> None:
        """
        Connect to the Sonoff LAN Mode Device and set up communication channel.
        """
        websocket_address = 'ws://%s:%s/' % (self.host, self.port)
        _LOGGER.debug('Connecting to websocket address: %s', websocket_address)

        self.websocket = yield from websockets.connect(websocket_address)
        yield from self._send_online_message(self.websocket, event_handler)
        yield from self._start_loop(self.websocket, event_handler)

    @asyncio.coroutine
    def _start_loop(self, websocket, event_handler):
        """
        We will listen for websockets events, sending a ping/pong every time
        we react to a TimeoutError. If we don't, the webserver would close the
        idle connection, forcing us to reconnect.
        """
        _LOGGER.debug('Starting websocket loop')
        while True:
            try:
                yield from asyncio.wait_for(
                    self._wait_for_message(websocket, event_handler),
                    timeout=self.DEFAULT_TIMEOUT
                )
            except asyncio.TimeoutError:
                yield from websocket.pong()
                _LOGGER.debug("Sending heartbeat...")
                continue

    @asyncio.coroutine
    def _send_online_message(self, websocket, event_handler):
        """
        Sends the user online message over the websocket.
        """
        _LOGGER.debug('Sending user online message over websocket')

        json_data = json.dumps(self.get_user_online_payload()).encode('utf8')
        yield from websocket.send(json_data)

        while True:
            response_message = yield from websocket.recv()
            response = json.loads(response_message)

            _LOGGER.debug('Received user online response:')
            _LOGGER.debug(response)
            # Example user online response:
            # {
            #     "error": 0,
            #     "apikey": "ab22d7b3-53de-44b9-ad26-f1ff260e8f1d",
            #     "sequence": "15483706231915703",
            #     "deviceid": "100040e943"
            # }

            # We want to pass the event to the event_handler already
            # because the hello event could arrive before the user online
            # confirmation response
            yield from event_handler(response_message)

            if ('error' in response and response['error'] == 0) \
                and 'deviceid' in response:
                _LOGGER.info('Websocket connected and accepted online user OK')
                return True
            else:
                _LOGGER.error('Websocket connection online user failed')

    @asyncio.coroutine
    def _wait_for_message(self, websocket, event_handler):
        _LOGGER.debug('Waiting for messages on websocket')
        while True:
            message = yield from websocket.recv()
            yield from event_handler(message)

    @asyncio.coroutine
    def send(self, request: Union[str, Dict]):
        """
        Send message to an already-connected Sonoff LAN Mode Device
        and return the response.

        :param request: command to send to the device (can be dict or json)
        :return:
        """
        if isinstance(request, dict):
            request = json.dumps(request).encode('utf8')

        _LOGGER.debug('Sending websocket message: %s', request)
        yield from self.websocket.send(request)

    @staticmethod
    def get_user_online_payload() -> Dict:
        return {
            'action': "userOnline",
            'userAgent': 'app',
            'version': 6,
            'nonce': ''.join([str(random.randint(0, 9)) for _ in range(15)]),
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
