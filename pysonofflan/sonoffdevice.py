"""
pysonofflan
Python library supporting Sonoff Smart Switches/Plugs (Basic/S20/Touch) in LAN Mode.
"""
import logging
from collections import defaultdict
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
                 client: Optional[SonoffLANModeClient] = None,
                 context: str = None) -> None:
        """
        Create a new SonoffDevice instance.

        :param str host: host name or ip address on which the device listens
        :param context: optional child ID for context in a parent device
        """
        self.host = host
        if not client:
            client = SonoffLANModeClient()
        self.client = client
        self.context = context

    def _update_helper(self,
                       payload: Optional[Dict] = None) -> Any:
        """
        Helper returning unwrapped result object and doing error handling.

        :param payload: JSON object passed as message to the device
        :return: Unwrapped result for the call.
        :rtype: dict
        :raises SonoffDeviceException: if command was not executed correctly
        """

        try:
            response = self.client.send(
                request=payload,
            )
        except Exception as ex:
            raise SonoffDeviceException('Communication error') from ex

        return response

    @property
    def basic_info(self) -> Dict[str, Any]:
        """
        Returns basic information about this device - only the ID is really useful for now.

        :return: Basic information dict.
        :rtype: dict
        """
        return defaultdict(lambda: None, self.get_basic_info())

    def get_basic_info(self) -> Dict:
        """
        Retrieve basic information about this device - only the ID is really useful for now.

        :return: basic_info
        :rtype dict
        :raises SonoffDeviceException: on error
        """
        return self.client.get_basic_info()

    @property
    def device_id(self) -> str:
        """
        Get current device ID (immutable value based on hardware MAC address)

        :return: Device ID.
        :rtype: str
        """
        return str(self.basic_info['device_id'])

    def turn_off(self) -> None:
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

    def turn_on(self) -> None:
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

    @property
    def state_information(self) -> Dict[str, Any]:
        """
        Returns device-type specific, end-user friendly state information.
        :return: dict with state information.
        :rtype: dict
        """
        raise NotImplementedError("Device subclass needs to implement this.")

    def __repr__(self):
        return "<%s at %s (%s), is_on: %s - dev specific: %s>" % (
            self.__class__.__name__,
            self.host,
            self.device_id,
            self.is_on,
            self.state_information)
