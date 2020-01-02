import sys
import socket
import threading
from flask import Flask, json, request
from zeroconf import ServiceBrowser, Zeroconf, ServiceInfo
from pysonofflan import sonoffcrypto

api = Flask(__name__)
device = None

@api.route('/zeroconf/switch', methods=['POST'])
def post_switch():

    print("Device %s, Received: %s" % (device._name, request.json))

    if request.json['deviceid'] == device._name:
        device.process_request(request.json)
    else:
        print("wrong device")

    return json.dumps({"seq":1,"sequence":"1577725767","error":0}), 200


class SonoffLANModeDeviceMock:

    def __init__(self, name, sonoff_type, api_key, ip, port):

        self._name = name 
        self._sonoff_type = sonoff_type
        self._api_key = api_key
        self._ip = ip
        self._port = port

        if self._name is None:
            self._name = ""

        self._name += "Mock"

        print("Device __init__ %s" % name)

        if self._sonoff_type is None:
            self._sonoff_type = "plug"

        if self._api_key == "None" or self._api_key is None:
            self._encrypt = False
        else:
            self._encrypt = True
            
        if self._ip is None:
            self._ip = "127.0.0.1"

        if self._port is None:
            self._port = 8081

        self._status = "off"


        self.register_on_network()


    def run_server(self):
        api.run(host=self._ip, port=self._port)


    def register_on_network(self):

        self._properties = dict(
            id = self._name,
            type = self._sonoff_type,
        )

        self.set_data()
        self._zeroconf_registrar = Zeroconf(interfaces=[self._ip])
        self._zeroconf_registrar.register_service(self.get_service_info())


    def get_service_info(self):

        type_ = "_ewelink._tcp.local."
        registration_name = "eWeLink_%s.%s" % (self._name, type_)

        service_info = ServiceInfo(
            type_, registration_name, socket.inet_aton(self._ip), port=self._port, properties=self._properties, server="eWeLink_" + self._name + ".local."
        )
        
        return service_info


    def set_data(self):

        if self._sonoff_type == "strip":

            self._properties['data1'] = b'{"sledOnline":"on","configure":[{"startup":"off","outlet":0},{"startup":"off","outlet":1},{"startup":"off","outlet":2},{"startup":"off","outlet":3}],'
            self._properties['data2'] = b'"pulses":[{"pulse":"off","width":1000,"outlet":0},{"pulse":"off","width":1000,"outlet":1},{"pulse":"off","width":1000,"outlet":2},{"pulse":"off","width":1000,"outlet":3}],'
        
            if self._status == "on":
                self._properties['data3'] = b'"switches":[{"switch":"on","outlet":0},{"switch":"off","outlet":1},{"switch":"off","outlet":2},{"switch":"on","outlet":3}]}'

            else:
                self._properties['data3'] = b'"switches":[{"switch":"off","outlet":0},{"switch":"off","outlet":1},{"switch":"off","outlet":2},{"switch":"on","outlet":3}]}'

        else:

            if self._status == "on":
                self._properties['data1'] = '{"switch":"on","startup":"stay","pulse":"off","sledOnline":"off","pulseWidth":500,"rssi":-55}'
            else:
                self._properties['data1'] = '{"switch":"off","startup":"stay","pulse":"off","sledOnline":"off","pulseWidth":500,"rssi":-55}'

        
        if self._encrypt:
            sonoffcrypto.format_encryption_txt(self._properties, self._api_key)
            print(self._properties)
       

    def get_status_from_data(self, data):

        if self._sonoff_type == "strip":
            return data['switches'][0]['switch']

        else:
            return data['switch']

    def process_request(self, json_):

        if json_['encrypt'] == True:
            iv = json_['iv']
            data = sonoffcrypto.decrypt(json_['data'], iv, self._api_key)
            import json
            data = json.loads(data)

        else:
            print(json_)
            data = json_['data']

        print(data)

        self._status = self.get_status_from_data(data)
        self.set_data()

        print("Updated Properties: %s" % self._properties)
   
        self._zeroconf_registrar.update_service(self.get_service_info())


def start_device(name = None, sonoff_type = None, api_key = None, ip = None, port = None):
      
    print("starting device: %s" % name)
    t = threading.Thread(target=start, args=(name, sonoff_type, api_key, ip, port))
    t.daemon = True
    t.start()
    print("device started: %s" % name)

def stop_device():

    print("stopping device")
    api.do_teardown_appcontext()
    global device
    device = None
    print("device stopped")

def start(name, sonoff_type, api_key, ip, port):

    global device
    device = SonoffLANModeDeviceMock(name, sonoff_type, api_key, ip, port)
    device.run_server()


if __name__ == '__main__':

    name = None
    sonoff_type = None
    api_key = None
    ip = None
    port = None

    try:
        name = sys.argv[1]
        sonoff_type = sys.argv[2]
        api_key = sys.argv[3]
        ip = sys.argv[4]
        port = int(sys.argv[5])
    except:
        pass

    start(name, sonoff_type, api_key, ip, port)
