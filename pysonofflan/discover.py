import ipaddress
import logging
import socket
from itertools import chain
from typing import Dict

_LOGGER = logging.getLogger(__name__)


class Discover:
    @staticmethod
    async def discover() -> Dict[str, str]:
        """
        Attempts websocket connection on port 8081 to all IP addresses on
        common home IP subnets: 192.168.0.X and 192.168.1.X, in the hope of
        detecting  available supported devices in the local network.

        :rtype: dict
        :return: Array of devices {"ip": "device_id"}
        """

        _LOGGER.debug("Attempting connection to all IPs on local network. "
                      "This will take approximately 1 minute, please wait...")
        devices = {}

        try:
            local_ip_ranges = chain(
                ipaddress.IPv4Network('127.0.0.1/32'),
                ipaddress.IPv4Network('192.168.0.0/24'),
                ipaddress.IPv4Network('192.168.1.0/24')
            )

            for ip in local_ip_ranges:
                _LOGGER.debug("Attempting connection to IP: %s" % ip)
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.1)
                result = sock.connect_ex((str(ip), 8081))
                if result == 0:
                    _LOGGER.info("Found open 8081 port at local IP: %s" % ip)
                    devices[ip] = ip
        except Exception as ex:
            _LOGGER.error("Caught Exception: %s" % ex, exc_info=False)

        return devices
