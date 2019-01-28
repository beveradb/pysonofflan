# -*- coding: utf-8 -*-

"""
pySonoffLAN
This module provides a way to interface with Sonoff smart home devices,
such as smart switches (e.g. Sonoff Basic), plugs (e.g. Sonoff S20), and wall switches (e.g. Sonoff Touch), 
when these devices are in LAN Mode.

LAN Mode is a feature introduced by manufacturer Itead, to allow operation locally when their servers are unavailable.
Further details can be found here: https://help.ewelink.cc/hc/en-us/articles/360007134171-LAN-Mode-Tutorial

Since mid 2018, the firmware Itead have shipped with most Sonoff devices has provided this feature,
allowing devices to be controlled directly on the local network using a WebSocket connection on port 8081.

The feature is designed to only be used when there is no connection to the Itead cloud servers,
(e.g. if your internet connection is down, or their servers are down).
As such, it is only enabled when the device is connected to your WiFi network, but *unable to reach the Itead servers*.
Most users will only be able to make use of this mode by deliberately blocking internet access to their Sonoff devices.

All common, shared functionality is available through `SonoffDevice` class:

    x = SonoffDevice("192.168.1.1")
    print(x.sys_info)

For device type specific actions `SonoffSwitch` must be used instead.

Module-specific errors are raised as `SonoffDeviceException` and are expected
to be handled by the user of the library.
"""

__author__ = """Andrew Beveridge"""
__email__ = 'andrew@beveridge.uk'
__version__ = '0.1.0'

# flake8: noqa
from .client import SonoffLANModeClient
from .discover import Discover
from .sonoffdevice import SonoffDevice, SonoffDeviceException
from .sonoffswitch import SonoffSwitch
