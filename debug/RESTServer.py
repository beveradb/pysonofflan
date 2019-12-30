from flask import Flask, json, request
from zeroconf import ServiceBrowser, Zeroconf, ServiceInfo
import socket


api = Flask(__name__)


@api.route('/zeroconf/switch', methods=['POST'])
def post_companies():

    print(request.json)

    if request.json['data']['switch'] == "on":
         properties['data1'] = '{"switch": "on"}'
    else:
         properties['data1'] = '{"switch": "off"}'

    #properties['data1'] = str(request.json['data'])

    print(properties)

    info_service = ServiceInfo(
        type_, registration_name, socket.inet_aton("127.0.0.1"), port=8081, properties=properties, server="eWeLink_" + name + ".local."
    )
    zeroconf_registrar.update_service(info_service)

    return json.dumps({"seq":41,"sequence":"1577725767","error":0}), 200

if __name__ == '__main__':

    type_ = "_ewelink._tcp.local."
    name = "TestDevice"
    registration_name = "eWeLink_%s.%s" % (name, type_)

    properties = dict(
        id=name,
        type="plug",
        encrypt=False,
        data1='{"switch": "off"}'
    )

    zeroconf_registrar = Zeroconf(interfaces=['127.0.0.1'])
    addresses = [socket.inet_aton("127.0.0.1")]
    info_service = ServiceInfo(
        type_, registration_name, socket.inet_aton("127.0.0.1"), port=8081, properties=properties, server="eWeLink_" + name + ".local."
    )
    zeroconf_registrar.register_service(info_service)

    api.run(port=8081)