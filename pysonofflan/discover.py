import ipaddress
import logging
import socket
import threading
import time
from itertools import chain
from typing import Dict
from datetime import datetime
from zeroconf import ServiceBrowser, Zeroconf


class Discover:

    @staticmethod
    async def discover(logger=None, seconds_to_wait=None) -> Dict[str, str]:
        """
        :rtype: dict
        :return: Array of devices {"device_id", "ip:port"}
        """
        if logger is None:
            print("new logger!")
            logger = logging.getLogger(__name__)

        logger.debug("Looking for all eWeLink devices on local network.")

        zeroconf = Zeroconf()
        listener = MyListener()
        listener.logger = logger
        ServiceBrowser(zeroconf, "_ewelink._tcp.local.", listener)

        if seconds_to_wait == None:
            time.sleep(4)

        else:
            time.sleep(seconds_to_wait)

        zeroconf.close()

        return listener.devices


class MyListener:

    def __init__(self):

        self.devices = {}


    def remove_service(self, zeroconf, type, name):

        print("%s - Service %s removed" % (datetime.now(), name) )


    def add_service(self, zeroconf, type, name):

        self.logger.debug("%s - Service %s added" % (datetime.now(), name) )
        info = zeroconf.get_service_info(type, name)
        self.logger.debug(info)
        device = info.properties[b'id'].decode('ascii')
        ip = self.parseAddress(info.address) + ":" + str(info.port)

        self.logger.info("Found Sonoff LAN Mode device %s at socket %s" % (device, ip))

        self.devices[device] = ip


    def parseAddress(self, address):
        """
        Resolve the IP address of the device
        :param address:
        :return: add_str
        """
        add_list = []
        for i in range(4):
            add_list.append(int(address.hex()[(i * 2):(i + 1) * 2], 16))
        add_str = str(add_list[0]) + "." + str(add_list[1]) + \
            "." + str(add_list[2]) + "." + str(add_list[3])
        return add_str



