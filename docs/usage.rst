=====
Usage
=====

Command-Line Usage
------------------
::

    Usage: pysonofflan [OPTIONS] COMMAND [ARGS]...

      A cli tool for controlling Sonoff Smart Switches/Plugs in LAN Mode.

    Options:
      --host TEXT          IP address or hostname of the device to connect to.
      --device_id TEXT     Device ID of the device to connect to.
      --inching TEXT       Number of seconds of "on" time if this is an
                           Inching/Momentary switch.
      -v, --verbosity LVL  Either CRITICAL, ERROR, WARNING, INFO or DEBUG
      --help               Show this message and exit.

    Commands:
      discover  Discover devices in the network (takes ~1...
      listen    Connect to device, print state, then print...
      off       Turn the device off.
      on        Turn the device on.
      state     Connect to device and print current state.

Install / Usage Example
=======================
::

    $ pip install pysonofflan

    $ pysonofflan discover
    2019-01-31 00:45:32,074 - info: Attempting to discover Sonoff LAN Mode devices on the local network, please wait...
    2019-01-31 00:46:24,007 - info: Found Sonoff LAN Mode device at IP 192.168.0.77

    $ pysonofflan --host 192.168.0.77 state
    2019-01-31 00:41:34,931 - info: Initialising SonoffSwitch with host 192.168.0.77
    2019-01-31 00:41:35,016 - info: == Device: 10006866e9 (192.168.0.77) ==
    2019-01-31 00:41:35,016 - info: State: OFF

    $ pysonofflan --host 192.168.0.77 on
    2019-01-31 00:49:40,334 - info: Initialising SonoffSwitch with host 192.168.0.77
    2019-01-31 00:49:40,508 - info:
    2019-01-31 00:49:40,508 - info: Initial state:
    2019-01-31 00:49:40,508 - info: == Device: 10006866e9 (192.168.0.77) ==
    2019-01-31 00:49:40,508 - info: State: OFF
    2019-01-31 00:49:40,508 - info:
    2019-01-31 00:49:40,508 - info: New state:
    2019-01-31 00:49:40,508 - info: == Device: 10006866e9 (192.168.0.77) ==
    2019-01-31 00:49:40,508 - info: State: ON

Library Usage
------------------

To use pySonoffLAN in a project::

    import pysonofflan


All common, shared functionality is available through :code:`SonoffSwitch` class::

    x = SonoffSwitch("192.168.1.50")

Upon instantiating the SonoffSwitch class, a connection is
initiated and device state is populated, but no further action is taken.

For most use cases, you'll want to make use of the :code:`callback_after_update`
parameter to do something with the device after a connection has been
initialised, for example::

    async def print_state_callback(device):
        if device.basic_info is not None:
            print("ON" if device.is_on else "OFF")
            device.shutdown_event_loop()

    SonoffSwitch(
        host="192.168.1.50",
        callback_after_update=print_state_callback
    )

This example simply connects to the device, prints whether it is currently
"ON" or "OFF", then closes the connection. Note, the callback must be
asynchronous.

Module-specific errors are raised as Exceptions, and are expected
to be handled by the user of the library.
