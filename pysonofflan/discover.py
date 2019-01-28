import json
import logging
import socket
from typing import Dict, Type

from pysonofflan import (SonoffLANModeClient)

_LOGGER = logging.getLogger(__name__)


class Discover:
    @staticmethod
    def discover(client: SonoffLANModeClient = None,
                 port: int = 8081,
                 timeout: int = 3) -> Dict[str, str]:
        """
        Sends discovery message to 255.255.255.255:8081 in order
        to detect available supported devices in the local network,
        and waits for given timeout for answers from devices.

        :param client: client implementation to use
        :param timeout: How long to wait for responses, defaults to 5
        :param port: port to send broadcast messages, defaults to 8081.
        :rtype: dict
        :return: Array of json objects {"ip", "port", "sys_info"}
        """
        if client is None:
            client = SonoffLANModeClient()

        target = "255.255.255.255"

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(timeout)

        user_online_payload = client.get_user_online_payload()
        req = json.dumps(user_online_payload)
        _LOGGER.debug("Sending discovery to %s:%s", target, port)

        sock.sendto(bytes(req, "utf-8"), (target, port))

        devices = {}
        _LOGGER.debug("Waiting %s seconds for responses...", timeout)

        try:
            while True:
                response, addr = sock.recvfrom(4096)
                ip, port = addr
                device_basic_info = json.loads(response)
                device_id = device_basic_info.device_id
                if device_id is not None:
                    devices[ip] = device_id
        except socket.timeout:
            _LOGGER.debug("Got socket timeout, which is okay.")
        except Exception as ex:
            _LOGGER.error("Got exception %s", ex, exc_info=True)
        return devices

    @staticmethod
    def discover_single(host: str,
                        client: SonoffLANModeClient = None
                        ) -> str:
        """
        Similar to discover(), except only return device object for a single
        host.

        :param host: Hostname of device to query
        :param client: client implementation to use
        :rtype: SmartDevice
        :return: Object for querying/controlling found device.
        """
        if client is None:
            client = SonoffLANModeClient()

        client.connect(host)
        info = client.get_basic_info()

        return info.device_id
