import ipaddress
import json
import logging
import socket
from typing import Dict

from pysonofflan import (SonoffLANModeClient)

_LOGGER = logging.getLogger(__name__)


class Discover:
    @staticmethod
    async def discover() -> Dict[str, str]:
        """
        Attempts websocket connection on port 8081 to all IP addresses on common home IP subnets:
        192.168.0.X and 192.168.1.X, in the hope of detecting  available supported devices in the local network.

        :param timeout: How long to wait for responses, defaults to 5 seconds
        :param port: port to send attempt connections on, defaults to 8081.
        :rtype: dict
        :return: Array of devices {"ip": "device_id"}
        """

        _LOGGER.debug("Attempting connection to all IPs on local network")
        devices = {}

        try:
            for ip in ipaddress.IPv4Network('192.168.0.0/23'):
                device_id = await Discover.discover_single(ip)
                if device_id is not None:
                    devices[ip] = device_id
        except Exception as ex:
            _LOGGER.error("Got exception %s", ex, exc_info=True)
        return devices

    @staticmethod
    async def discover_single(host: str) -> str:
        """
        Attempt to connect to a single host, returning device ID if successful.

        :param host: Hostname / IP address of device to query
        :rtype: str
        :return: Device ID of found device
        """

        client = SonoffLANModeClient(host)
        await client.connect()
        info = await client.get_basic_info()

        return info.device_id
