import ipaddress
import json
import logging
import socket
from itertools import chain
from typing import Dict, Optional

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
            local_ip_ranges = chain(
                ipaddress.IPv4Network('127.0.0.1/32'),
                ipaddress.IPv4Network('192.168.0.0/24'),
                ipaddress.IPv4Network('192.168.1.0/24')
            )

            for ip in local_ip_ranges:
                _LOGGER.debug("Attempting connection to IP: %s" % ip)
                device_info = await Discover.discover_single(ip)
                if device_info is not None:
                    devices[ip] = device_info['deviceid']
        except Exception as ex:
            _LOGGER.error("Caught Exception: %s" % ex, exc_info=False)

        return devices

    @staticmethod
    async def discover_single(host: str) -> Optional[dict]:
        """
        Attempt to connect to a single host, returning device ID if successful.

        :param host: Hostname / IP address of device to query
        :rtype: str
        :return: Device ID of found device
        """

        info = None

        try:
            client = SonoffLANModeClient(host)
            await client.connect(connect_timeout=1)
            info = await client.get_basic_info()
        except ConnectionRefusedError as ex:
            _LOGGER.error("Got ConnectionRefusedError %s", ex, exc_info=False)

        return info
