"""
pysonofflan
Python library supporting Sonoff Smart Devices (Basic/S20/Touch) in LAN Mode.
"""
import logging
from typing import Any, Dict, Optional

from .client import SonoffLANModeClient

_LOGGER = logging.getLogger(__name__)


class SonoffDeviceException(Exception):
    """
    SonoffDeviceException gets raised for errors reported by device.
    """
    pass


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

    async def _update_helper(self, payload: Optional[Dict] = None) -> Any:
        """
        Helper returning unwrapped result object and doing error handling.

        :param payload: JSON object passed as message to the device
        :return: Unwrapped result for the call.
        :rtype: dict
        :raises SonoffDeviceException: if command was not executed correctly
        """

        try:
            response = await self.client.send(request=payload)
        except Exception as ex:
            raise SonoffDeviceException('Unable to connect to Sonoff') from ex

        return response

    async def get_basic_info(self) -> dict:
        """
        Retrieve basic information about this device - only ID is really
        useful for now.

        :return: basic_info
        :rtype dict
        :raises SonoffDeviceException: on error
        """
        try:
            basic_info = await self.client.get_basic_info()
        except Exception as ex:
            raise SonoffDeviceException('Unable to connect to Sonoff') from ex
        return basic_info

    @property
    async def device_id(self) -> str:
        """
        Get current device ID (immutable value based on hardware MAC address)

        :return: Device ID.
        :rtype: str
        """
        try:
            basic_info = await self.get_basic_info()
        except Exception as ex:
            raise SonoffDeviceException('Unable to connect to Sonoff') from ex

        return str(basic_info['deviceid'])

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
        return "<%s at %s (%s), is_on: %s>" % (
            self.__class__.__name__,
            self.host,
            self.device_id,
            self.is_on)
