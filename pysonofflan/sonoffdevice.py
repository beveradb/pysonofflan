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
                 context: str = None) -> None:
        """
        Create a new SonoffDevice instance.

        :param str host: host name or ip address on which the device listens
        :param context: optional child ID for context in a parent device
        """
        self.host = host
        self.context = context
        self.client = SonoffLANModeClient(host)
        self.basic_info = None
        self.params = None

        _LOGGER.info('Calling connect in SonoffLANModeClient with handler')
        asyncio.get_event_loop().run_until_complete(
            self.client.connect(self.handle_message)
        )
        asyncio.get_event_loop().run_forever()

    def handle_message(self, message):
        """
        Receive message sent by the device and handle it, either updating
        state or storing basic device info
        """
        response = json.loads(message)

        if ('error' in response and response['error'] == 0) \
            and 'deviceid' in response:
            _LOGGER.info('Received basic device info, storing in instance')
            self.basic_info = response
        elif 'action' in response and response['action'] == "update":
            _LOGGER.info('Received update action, updating internal state')
            self.params = response['params']
        else:
            _LOGGER.error('Unknown message received from device: ' % message)
            raise Exception('Unknown message received from device')

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
