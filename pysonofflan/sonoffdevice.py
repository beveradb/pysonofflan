"""
pysonofflan
Python library supporting Sonoff Smart Devices (Basic/S20/Touch) in LAN Mode.
"""
import asyncio
import json
import logging
from typing import Callable, Awaitable, Dict

import websockets

from .client import SonoffLANModeClient


class SonoffDevice(object):
    def __init__(self,
                 host: str,
                 callback_after_update: Callable[..., Awaitable[None]] = None,
                 shared_state: Dict = None,
                 logger=None,
                 loop=None,
                 ping_interval=SonoffLANModeClient.DEFAULT_PING_INTERVAL,
                 timeout=SonoffLANModeClient.DEFAULT_TIMEOUT,
                 context: str = None) -> None:
        """
        Create a new SonoffDevice instance.

        :param str host: host name or ip address on which the device listens
        :param context: optional child ID for context in a parent device
        """
        self.callback_after_update = callback_after_update
        self.host = host
        self.context = context
        self.shared_state = shared_state
        self.basic_info = None
        self.params = {}
        self.send_updated_params_task = None
        self.params_updated_event = None
        self.loop = loop

        if logger is None:
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = logger

        self.logger.debug(
            'Initializing SonoffLANModeClient class in SonoffDevice')
        self.client = SonoffLANModeClient(
            host,
            self.handle_message,
            ping_interval=ping_interval,
            timeout=timeout,
            logger=self.logger
        )

        try:
            if self.loop is None:
                self.loop = asyncio.new_event_loop()

            asyncio.set_event_loop(self.loop)

            self.params_updated_event = asyncio.Event()
            self.send_updated_params_task = self.loop.create_task(
                self.send_updated_params_loop()
            )

            if not self.loop.is_running():
                self.loop.run_until_complete(self.setup_connection())
            else:
                asyncio.ensure_future(self.setup_connection())

        except asyncio.CancelledError:
            self.logger.debug('SonoffDevice loop ended, returning')

    async def setup_connection(self):
        self.logger.debug('setup_connection is active on the event loop')

        waits=0
        
        while True:
                                
            for tries in range(1,3):                                                            # MJS: upto 3 immediate retries before a wait            
           
                try:
                    self.logger.debug('setup_connection yielding to connect(), try: %i, waits %i', tries, waits)
                    await self.client.connect()
                    self.logger.debug(
                        'setup_connection yielding to send_online_message()')
                    await self.client.send_online_message()
                    self.logger.debug(
                        'setup_connection yielding to receive_message_loop()')
                    await self.client.receive_message_loop()

                except websockets.InvalidMessage as ex:
                    self.logger.error('Unable to connect: %s' % ex)
                    break                                                                       # wait before rety
                except ConnectionRefusedError:
                    self.logger.error('Unable to connect: connection refused')
                    break                                                                       # wait before retry
                except websockets.exceptions.ConnectionClosed:
                    self.logger.error('Connection closed unexpectedly in setup_connection')
                                                                                                # retry immediately
                finally:
                    self.logger.debug('finally: closing websocket from setup_connection')
                    await self.client.close_connection()
            
            self.logger.debug('waiting 60 seconds before trying again')
            await asyncio.sleep(60)
            waits+=1        
        
        self.shutdown_event_loop() # this is causing HA to hang and sometimes not be restartable 
        self.logger.debug('existing setup_connection()')
                
    async def send_updated_params_loop(self):
        self.logger.debug(
            'send_updated_params_loop is active on the event loop')

        try:
            self.logger.debug(
                'Starting loop waiting for device params to change')
            while self.client.keep_running:
                self.logger.debug(
                    'send_updated_params_loop now awaiting event')
                await self.params_updated_event.wait()

                update_message = self.client.get_update_payload(
                    self.device_id,
                    self.params
                )
                self.params_updated_event.clear() # MJS: Clear event before we try send, this is so new event whilst send is blocked is stacked up
                
                try:
                    await self.client.send(update_message)
                
                except websockets.exceptions.ConnectionClosed:                                  # MJS: Added exception handling so to avoid terminating the 
                    self.logger.warn('Connection closed unexpectedly in send()')
                    
                except Exception as ex:
                    self.logger.error('Unexpected error in send(): %s', format(ex) )

                self.logger.debug('Update message sent, event cleared, should '
                                  'loop now')
        finally:
            self.logger.debug(
                'send_updated_params_loop finally block reached: '
                'closing websocket')
            await self.client.close_connection()

        self.logger.debug(
            'send_updated_params_loop resumed outside loop, exiting')

    def update_params(self, params):
        self.logger.debug(
            'Scheduling params update message to device: %s' % params
        )
        self.params = params
        self.params_updated_event.set()

    async def handle_message(self, message):
        """
        Receive message sent by the device and handle it, either updating
        state or storing basic device info
        """
        response = json.loads(message)

        if (
            ('error' in response and response['error'] == 0)
            and 'deviceid' in response
        ):
            self.logger.debug(
                'Received basic device info, storing in instance')
            self.basic_info = response
        elif 'action' in response and response['action'] == "update":
            self.logger.debug(
                'Received update from device, updating internal state to: %s'
                % response['params'])
            self.params = response['params']

            if self.callback_after_update is not None:
                await self.callback_after_update(self)
        else:
            self.logger.error(
                'Unknown message received from device: ' % message)
            raise Exception('Unknown message received from device')

    def shutdown_event_loop(self):
        self.logger.debug(
            'shutdown_event_loop called, setting keep_running to '
            'False')
        self.client.keep_running = False

        try:
            # Hide Cancelled Error exceptions during shutdown
            def shutdown_exception_handler(loop, context):
                if "exception" not in context \
                    or not isinstance(context["exception"],
                                      asyncio.CancelledError):
                    loop.default_exception_handler(context)

            self.loop.set_exception_handler(shutdown_exception_handler)

            # Handle shutdown gracefully by waiting for all tasks
            # to be cancelled
            tasks = asyncio.gather(
                *asyncio.all_tasks(loop=self.loop),
                loop=self.loop,
                return_exceptions=True
            )

            tasks.add_done_callback(lambda t: self.loop.stop())
            tasks.cancel()

            # Keep the event loop running until it is either
            # destroyed or all tasks have really terminated
            while (
                not tasks.done()
                and not self.loop.is_closed()
                and not self.loop.is_running()
            ):
                self.loop.run_forever()
        finally:
            if (
                hasattr(self.loop, "shutdown_asyncgens")
                and not self.loop.is_running()
            ):
                # Python 3.5
                self.loop.run_until_complete(
                    self.loop.shutdown_asyncgens()
                )
                self.loop.close()

    @property
    def device_id(self) -> str:
        """
        Get current device ID (immutable value based on hardware MAC address)

        :return: Device ID.
        :rtype: str
        """
        return self.basic_info['deviceid']

    async def turn_off(self) -> None:
        """
        Turns the device off.
        """
        raise NotImplementedError("Device subclass needs to implement this.")

    @property
    def is_off(self) -> bool:
        """
        Returns whether device is off.

        :return: True if device is off, False otherwise.
        :rtype: bool
        """
        return not self.is_on

    async def turn_on(self) -> None:
        """
        Turns the device on.
        """
        raise NotImplementedError("Device subclass needs to implement this.")

    @property
    def is_on(self) -> bool:
        """
        Returns whether the device is on.

        :return: True if the device is on, False otherwise.
        :rtype: bool
        :return:
        """
        raise NotImplementedError("Device subclass needs to implement this.")

    def __repr__(self):
        return "<%s at %s>" % (
            self.__class__.__name__,
            self.host)
