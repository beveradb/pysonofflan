import asyncio
import binascii
import json
import logging
import random
import time
from typing import Dict, Union, Callable, Awaitable

import websockets
from websockets.framing import OP_CLOSE, parse_close, OP_PING, OP_PONG

_LOGGER = logging.getLogger(__name__)


class SonoffLANModeClientProtocol(websockets.WebSocketClientProtocol):
    """WebSocket client protocol which ignores pong payload."""

    @asyncio.coroutine
    def read_data_frame(self, max_size):
        """
        Copied from WebSocketCommonProtocol to change pong handling
        """
        # 6.2. Receiving Data
        while True:
            frame = yield from self.read_frame(max_size)

            if frame.opcode == OP_CLOSE:
                self.close_code, self.close_reason = parse_close(frame.data)
                yield from self.write_close_frame(frame.data)
                return

            elif frame.opcode == OP_PING:
                ping_hex = binascii.hexlify(frame.data).decode() or '[empty]'
                _LOGGER.debug(
                    "%s - received ping, sending pong: %s", self.side, ping_hex
                )
                yield from self.pong(frame.data)

            elif frame.opcode == OP_PONG:
                # Acknowledge pings on solicited pongs, regardless of payload
                if self.pings:
                    ping_id, pong_waiter = self.pings.popitem(0)
                    ping_hex = binascii.hexlify(ping_id).decode() or '[empty]'
                    pong_waiter.set_result(None)
                    _LOGGER.debug(
                        "%s - received pong, clearing most recent ping: %s",
                        self.side,
                        ping_hex
                    )
                else:
                    _LOGGER.debug(
                        "%s - received pong, but no pings to clear",
                        self.side
                    )
            else:
                return frame


class SonoffLANModeClient:
    """
    Implementation of the Sonoff LAN Mode Protocol (as used by the eWeLink app)
    """
    DEFAULT_PORT = 8081
    DEFAULT_TIMEOUT = 10

    """
    Initialise class with connection parameters

    :param str host: host name or ip address of the device
    :param int port: port on the device (default: 8081)
    :return:
    """

    def __init__(self, host: str,
                 event_handler: Callable[[str], Awaitable[None]],
                 port: int = DEFAULT_PORT):
        self.host = host
        self.port = port
        self.websocket = None
        self.keep_running = True
        self.event_handler = event_handler

    @asyncio.coroutine
    def connect(self):
        """
        Connect to the Sonoff LAN Mode Device and set up communication channel.
        """
        websocket_address = 'ws://%s:%s/' % (self.host, self.port)
        _LOGGER.debug('Connecting to websocket address: %s', websocket_address)

        self.websocket = yield from websockets.connect(
            websocket_address,
            ping_interval=5,
            ping_timeout=10,
            subprotocols=['chat'],
            klass=SonoffLANModeClientProtocol
        )

        try:
            yield from self._send_online_message()
            yield from self._start_loop()
        finally:
            _LOGGER.debug('Closing websocket from connect finally block')
            yield from self.websocket.close()

    @asyncio.coroutine
    def close_connection(self):
        _LOGGER.debug('Closing websocket from close_connection')
        yield from self.websocket.close()

    @asyncio.coroutine
    def _start_loop(self):
        """
        We will listen for websockets events, sending a ping/pong every time
        we react to a TimeoutError. If we don't, the webserver would close the
        idle connection, forcing us to reconnect.
        """
        while self.keep_running:
            _LOGGER.debug('Starting websocket client wait for message loop')
            try:
                yield from self._wait_for_message(
                    self.websocket,
                    self.event_handler
                )
            finally:
                yield from self.websocket.close()

    @asyncio.coroutine
    def _send_online_message(self):
        """
        Sends the user online message over the websocket.
        """
        _LOGGER.debug('Sending user online message over websocket')

        json_data = json.dumps(self.get_user_online_payload())
        yield from self.websocket.send(json_data)

        response_message = yield from self.websocket.recv()
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
        yield from self.event_handler(response_message)

        if ('error' in response and response['error'] == 0) \
            and 'deviceid' in response:
            _LOGGER.debug('Websocket connected and accepted online user OK')
            return True
        else:
            _LOGGER.error('Websocket connection online user failed')

    @asyncio.coroutine
    def _wait_for_message(self, websocket, event_handler):
        try:
            while self.keep_running:
                _LOGGER.debug('Waiting for messages on websocket')
                message = yield from websocket.recv()
                yield from event_handler(message)
        finally:
            yield from self.websocket.close()

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

# Uncomment the below to test this websocket client directly on CLI

# async def print_event_handler(message: str):
#     print("CALLBACK SUCCESS! Message: %s" % message)
#
# logging.basicConfig(level=logging.DEBUG)  # Shows debug logs from websocket
# _LOGGER.setLevel(logging.DEBUG)
# handler = logging.StreamHandler(sys.stdout)
# handler.setLevel(logging.DEBUG)
# formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
# handler.setFormatter(formatter)
# _LOGGER.addHandler(handler)
# client = SonoffLANModeClient('127.0.0.1', print_event_handler)
# # client = SonoffLANModeClient('192.168.0.76', print_event_handler)
#
# asyncio.get_event_loop().run_until_complete(client.connect())
# asyncio.get_event_loop().run_forever()
