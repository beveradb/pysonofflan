import binascii
import json
import logging
import random
import time
from typing import Dict, Union, Callable, Awaitable
import asyncio
import enum

import websockets
from websockets.framing import OP_CLOSE, parse_close, OP_PING, OP_PONG

logger = logging.getLogger(__name__)

V6_DEFAULT_TIMEOUT = 10
V6_DEFAULT_PING_INTERVAL = 300

class InvalidState(Exception):
    """
    Exception raised when an operation is forbidden in the current state.
    """
    
CLOSE_CODES = {
    1000: "OK",
    1001: "going away",
    1002: "protocol error",
    1003: "unsupported type",
    # 1004 is reserved
    1005: "no status code [internal]",
    1006: "connection closed abnormally [internal]",
    1007: "invalid data",
    1008: "policy violation",
    1009: "message too big",
    1010: "extension required",
    1011: "unexpected error",
    1015: "TLS failure [internal]",
}

# A WebSocket connection goes through the following four states, in order:

class State(enum.IntEnum):
    CONNECTING, OPEN, CLOSING, CLOSED = range(4)

class ConnectionClosed(InvalidState):
    """
    Exception raised when trying to read or write on a closed connection.
    Provides the connection close code and reason in its ``code`` and
    ``reason`` attributes respectively.
    """

    def __init__(self, code, reason):
        self.code = code
        self.reason = reason
        message = "WebSocket connection is closed: "
        message += format_close(code, reason)
        super().__init__(message)

def format_close(code, reason):
    """
    Display a human-readable version of the close code and reason.
    """
    if 3000 <= code < 4000:
        explanation = "registered"
    elif 4000 <= code < 5000:
        explanation = "private use"
    else:
        explanation = CLOSE_CODES.get(code, "unknown")
    result = "code = {} ({}), ".format(code, explanation)

    if reason:
        result += "reason = {}".format(reason)
    else:
        result += "no reason"

    return result

class SonoffLANModeClientProtocol(websockets.WebSocketClientProtocol):
    """Customised WebSocket client protocol to ignore pong payload match."""

    @asyncio.coroutine
    def read_data_frame(self, max_size):
        """
        Copied from websockets.WebSocketCommonProtocol to change pong handling
        """
        while True:
            frame = yield from self.read_frame(max_size)

            if frame.opcode == OP_CLOSE:
                self.close_code, self.close_reason = parse_close(frame.data)
                yield from self.write_close_frame(frame.data)
                return

            elif frame.opcode == OP_PING:
                ping_hex = binascii.hexlify(frame.data).decode() or '[empty]'
                logger.debug(
                    "%s - received ping, sending pong: %s", self.side, ping_hex
                )
                yield from self.pong(frame.data)

            elif frame.opcode == OP_PONG:
                # Acknowledge pings on solicited pongs, regardless of payload
                if self.pings:
                    ping_id, pong_waiter = self.pings.popitem(0)
                    ping_hex = binascii.hexlify(ping_id).decode() or '[empty]'
                    pong_waiter.set_result(None)
                    logger.debug(
                        "%s - received pong, clearing most recent ping: %s",
                        self.side,
                        ping_hex
                    )
                else:
                    logger.debug(
                        "%s - received pong, but no pings to clear",
                        self.side
                    )
            else:
                return frame

    def __init__(self, **kwds):

        logger.debug("__init__()" )

        if float(websockets.__version__) < 7.0:

            self.ping_interval = V6_DEFAULT_PING_INTERVAL
            self.ping_timeout = V6_DEFAULT_TIMEOUT

            #self.close_code: int
            #self.close_reason: str

            # Task sending keepalive pings.
            self.keepalive_ping_task = None

        super().__init__(**kwds)

    def connection_open(self):

        logger.debug("connection_open()")

        super().connection_open()

        if float(websockets.__version__) < 7.0:

            # Start the task that sends pings at regular intervals.
            self.keepalive_ping_task = asyncio.ensure_future(
                self.keepalive_ping(), loop=self.loop
            )

    @asyncio.coroutine
    def keepalive_ping(self):

        logger.debug("keepalive_ping()" )

        if float(websockets.__version__) >= 7.0:

            super().keepalive_ping()

        else:

            """
            Send a Ping frame and wait for a Pong frame at regular intervals.
            This coroutine exits when the connection terminates and one of the
            following happens:
            - :meth:`ping` raises :exc:`ConnectionClosed`, or
            - :meth:`close_connection` cancels :attr:`keepalive_ping_task`.
            """
            if self.ping_interval is None:
                return

            try:
                while True:

                    yield from asyncio.sleep(self.ping_interval, loop=self.loop)

                    # ping() cannot raise ConnectionClosed, only CancelledError:
                    # - If the connection is CLOSING, keepalive_ping_task will be
                    #   canceled by close_connection() before ping() returns.
                    # - If the connection is CLOSED, keepalive_ping_task must be
                    #   canceled already.

                    ping_waiter = yield from self.ping()

                    if self.ping_timeout is not None:
                        try:
                            yield from asyncio.wait_for(
                                ping_waiter, self.ping_timeout, loop=self.loop
                            )

                        except asyncio.TimeoutError:
                            logger.debug("%s ! timed out waiting for pong", self.side)
                            self.fail_connection(1011)
                            break

            except asyncio.CancelledError:
                raise

            except Exception:
                logger.warning("Unexpected exception in keepalive ping task", exc_info=True)

    @asyncio.coroutine
    def close_connection(self):

        logger.debug("close_connection()")

        yield from super().close_connection()

        logger.debug("super.close_connection() finished" )

        if float(websockets.__version__) < 7.0:

            # Cancel the keepalive ping task.
            if self.keepalive_ping_task is not None:
                self.keepalive_ping_task.cancel()



    def abort_keepalive_pings(self):

        logger.debug("abort_keepalive_pings()")

        if float(websockets.__version__) >= 7.0:
            super().abort_keepalive_pings()

        else:

            """
            Raise ConnectionClosed in pending keepalive pings.
            They'll never receive a pong once the connection is closed.
            """
            assert self.state is State.CLOSED
            exc = ConnectionClosed(self.close_code, self.close_reason)
            exc.__cause__ = self.transfer_data_exc  # emulate raise ... from ...

            try:

                for ping in self.pings.values():
                    ping.set_exception(exc)

            except asyncio.InvalidStateError:
                pass

            """ No Need to do this as in V6, this is done in super.close_connection()

            if self.pings:
                pings_hex = ', '.join(
                    binascii.hexlify(ping_id).decode() or '[empty]'
                    for ping_id in self.pings
                )
                plural = 's' if len(self.pings) > 1 else ''
                logger.debug(
                    "%s - aborted pending ping%s: %s", self.side, plural, pings_hex
                )"""

    def connection_lost(self, exc):

        logger.debug("connection_lost()" )

        if float(websockets.__version__) < 7.0:

            logger.debug("%s - event = connection_lost(%s)", self.side, exc)
            self.state = State.CLOSED
            logger.debug("%s - state = CLOSED", self.side)
            if self.close_code is None:
                self.close_code = 1006
            if self.close_reason is None:
                self.close_reason = ""
            logger.debug(
                "%s x code = %d, reason = %s",
                self.side,
                self.close_code,
                self.close_reason or "[no reason]",
            )   

            self.abort_keepalive_pings()

        super().connection_lost(exc)



class SonoffLANModeClient:
    """
    Implementation of the Sonoff LAN Mode Protocol (as used by the eWeLink app)
    """
    DEFAULT_PORT = 8081
    DEFAULT_TIMEOUT = 5
    DEFAULT_PING_INTERVAL = 5

    """
    Initialise class with connection parameters

    :param str host: host name or ip address of the device
    :param int port: port on the device (default: 8081)
    :return:
    """

    def __init__(self, host: str,
                 event_handler: Callable[[str], Awaitable[None]],
                 port: int = DEFAULT_PORT,
                 ping_interval: int = DEFAULT_PING_INTERVAL,
                 timeout: int = DEFAULT_TIMEOUT,
                 logger: logging.Logger = None):
        self.host = host
        self.port = port
        self.ping_interval = ping_interval
        self.timeout = timeout
        self.logger = logger
        self.websocket = None
        self.event_handler = event_handler
        self.connected_event = asyncio.Event()
        self.disconnected_event = asyncio.Event()


        if self.logger is None:
            self.logger = logging.getLogger(__name__)

    async def connect(self):
        """
        Connect to the Sonoff LAN Mode Device and set up communication channel.
        """
        websocket_address = 'ws://%s:%s/' % (self.host, self.port)
        self.logger.debug('Connecting to websocket address: %s',
                          websocket_address)

        try:
            if float(websockets.__version__) >= 7.0:
                self.websocket = await websockets.connect(
                    websocket_address,
                    ping_interval=self.ping_interval,
                    ping_timeout=self.timeout,
                    subprotocols=['chat'],
                    klass=SonoffLANModeClientProtocol
                )
            else:
                self.websocket = await websockets.connect(
                    websocket_address,
                    timeout=self.timeout,
                    subprotocols=['chat'],
                    klass=SonoffLANModeClientProtocol
                )
        except websockets.InvalidMessage as ex:
            self.logger.error('SonoffLANModeClient connection failed: %s' % ex)
            raise ex

    async def close_connection(self):
        self.logger.debug('Closing websocket from client close_connection')
        self.connected_event.clear()
        self.disconnected_event.set()
        if self.websocket is not None:
            self.logger.debug('calling websocket.close')
            await self.websocket.close()
            self.websocket = None                       # Ensure we cannot close multiple times
            self.logger.debug('websocket was closed')
            
    async def receive_message_loop(self):
        try:
            while True:
                self.logger.debug('Waiting for messages on websocket')
                message = await self.websocket.recv()
                await self.event_handler(message)
                self.logger.debug('Message passed to handler, should loop now')
        finally:
            self.logger.debug('receive_message_loop finally block reached')

    async def send_online_message(self):
        self.logger.debug('Sending user online message over websocket')

        json_data = json.dumps(self.get_user_online_payload())
        await self.websocket.send(json_data)

        response_message = await self.websocket.recv()
        response = json.loads(response_message)

        self.logger.debug('Received user online response:')
        self.logger.debug(response)
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
        await self.event_handler(response_message)

        if (
            ('error' in response and response['error'] == 0)
            and 'deviceid' in response
        ):
            self.logger.debug(
                'Websocket connected and accepted online user OK')
            return True
        else:
            self.logger.error('Websocket connection online user failed')

    async def send(self, request: Union[str, Dict]):
        """
        Send message to an already-connected Sonoff LAN Mode Device
        and return the response.

        :param request: command to send to the device (can be dict or json)
        :return:
        """
        if isinstance(request, dict):
            request = json.dumps(request)

        self.logger.debug('Sending websocket message: %s', request)
        await self.websocket.send(request)

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
