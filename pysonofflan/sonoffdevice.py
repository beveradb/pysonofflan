"""
pysonofflan
Python library supporting Sonoff Smart Devices (Basic/S20/Touch) in LAN Mode.
"""
import asyncio
import json
import logging

from .client import SonoffLANModeClient

_LOGGER = logging.getLogger(__name__)


class SonoffDevice(object):
    def __init__(self,
                 host: str,
                 end_after_first_update: bool = False,
                 context: str = None) -> None:
        """
        Create a new SonoffDevice instance.

        :param str host: host name or ip address on which the device listens
        :param context: optional child ID for context in a parent device
        """
        self.host = host
        self.context = context
        self.basic_info = None
        self.params = None
        self.end_after_first_update = end_after_first_update

        _LOGGER.debug('Calling connect in SonoffLANModeClient with handler')
        self.client = SonoffLANModeClient(host, self.handle_message)

        try:
            self.loop = asyncio.new_event_loop()
            self.loop.run_until_complete(self.client.connect())
            self.loop.run_forever()
        except asyncio.CancelledError:
            _LOGGER.debug('SonoffDevice loop ended, returning')

    @asyncio.coroutine
    def update_params(self, params):
        update_message = self.client.get_update_payload(
            self.device_id,
            params
        )

        _LOGGER.info(
            'Sending params update message to device: %s' % update_message
        )

        yield from self.client.send(update_message)

    @asyncio.coroutine
    def handle_message(self, message):
        """
        Receive message sent by the device and handle it, either updating
        state or storing basic device info
        """
        response = json.loads(message)

        if ('error' in response and response['error'] == 0) \
            and 'deviceid' in response:
            _LOGGER.debug('Received basic device info, storing in instance')
            self.basic_info = response
        elif 'action' in response and response['action'] == "update":
            _LOGGER.debug(
                'Received update action, updating internal params state to: %s'
                % response['params'])
            self.params = response['params']

            if self.end_after_first_update:
                _LOGGER.debug('Gracefully stopping message receive loop')
                self.shutdown_loop()
        else:
            _LOGGER.error('Unknown message received from device: ' % message)
            raise Exception('Unknown message received from device')

    def shutdown_loop(self):
        self.client.keep_running = False

        try:
            # Hide `asyncio.CancelledError` exceptions during shutdown
            def shutdown_exception_handler(loop, context):
                if "exception" not in context \
                    or not isinstance(context["exception"],
                                      asyncio.CancelledError):
                    loop.default_exception_handler(context)

            self.loop.set_exception_handler(shutdown_exception_handler)

            # Handle shutdown gracefully by waiting for all tasks
            # to be cancelled
            tasks = asyncio.gather(
                *asyncio.Task.all_tasks(loop=self.loop),
                loop=self.loop,
                return_exceptions=True
            )

            tasks.add_done_callback(lambda t: self.loop.stop())
            tasks.cancel()

            # Keep the event loop running until it is either
            # destroyed or all tasks have really terminated
            while not tasks.done() and not self.loop.is_closed():
                self.loop.run_forever()
        finally:
            if hasattr(self.loop, "shutdown_asyncgens"):  # Python 3.5
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
    async def is_off(self) -> bool:
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
    async def is_on(self) -> bool:
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
