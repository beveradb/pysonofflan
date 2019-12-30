from datetime import datetime
import time
from zeroconf import ServiceBrowser, Zeroconf, ServiceInfo

class MyListener:

    info = None
    devices = {}

    def remove_service(self, zeroconf, type, name):

        print("%s - Service %s removed" % (datetime.now(), name) )


    def add_service(self, zeroconf, type, name):

        print("%s - Service %s added" % (datetime.now(), name) )
        info = zeroconf.get_service_info(type, name)
        print(info)
        device = info.properties[b'id'].decode('ascii')
        ip = self.parseAddress(info.address) + ":" + str(info.port)

        self.devices[device] = ip

        ServiceBrowser(zeroconf, name, listener)


    def update_service(self, zeroconf, type, name):

        print("%s - Service %s updated" % (datetime.now(), name) )
        info = zeroconf.get_service_info(type, name)
        print(info)

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


zeroconf = Zeroconf()
listener = MyListener()
browser = ServiceBrowser(zeroconf, "_ewelink._tcp.local.", listener)

try:
    input("Press enter to exit...\n\n")
    print(listener.devices)

finally:
    zeroconf.close()

