from datetime import datetime

from zeroconf import ServiceBrowser, Zeroconf

class MyListener:

    info = None

    def remove_service(self, zeroconf, type, name):

        if name == 'eWeLink_100065a8e3._ewelink._tcp.local.':
            print("%s - Service %s removed" % (datetime.now(), name) )

    def add_service(self, zeroconf, type, name):

        if name == 'eWeLink_100065a8e3._ewelink._tcp.local.':
            print("%s - Service %s added" % (datetime.now(), name) )

        # 
        # print(zeroconf.get_service_info(type, name))
        
        ServiceBrowser(zeroconf, name, listener)

    def update_service(self, zeroconf, type, name):

        if name == 'eWeLink_100065a8e3._ewelink._tcp.local.a':
            print("%s - Service %s updated" % (datetime.now(), name) )

        # print(zeroconf.get_service_info(type, name))
        
zeroconf = Zeroconf()
listener = MyListener()
browser = ServiceBrowser(zeroconf, "_ewelink._tcp.local.", listener)

try:
    input("Press enter to exit...\n\n")

finally:
    zeroconf.close()




