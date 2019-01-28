import datetime
import logging
from typing import Any, Dict, Optional

from pysonofflan import SonoffDevice, SonoffLANModeClient

_LOGGER = logging.getLogger(__name__)


class SonoffSwitch(SonoffDevice):
    """Representation of a Sonoff Smart Switch/Plug/Wall Switch in LAN Mode.

    Usage example when used as library:
    p = SonoffSwitch("192.168.1.105")
    # print the device ID
    print(p.device_id)
    # change state of plug
    p.state = "ON"
    p.state = "OFF"
    # query and print current state of plug
    print(p.state)

    Errors reported by the device are raised as SonoffDeviceExceptions,
    and should be handled by the user of the library.
    """
    # switch states
    SWITCH_STATE_ON = 'ON'
    SWITCH_STATE_OFF = 'OFF'
    SWITCH_STATE_UNKNOWN = 'UNKNOWN'

    def __init__(self,
                 host: str,
                 client: 'SonoffLANModeClient' = None,
                 context: str = None) -> None:
        SonoffDevice.__init__(self, host, client, context)

    @property
    def state(self) -> str:
        """
        Retrieve the switch state

        :returns: one of
                  SWITCH_STATE_ON
                  SWITCH_STATE_OFF
                  SWITCH_STATE_UNKNOWN
        :rtype: str
        """
        state = self.basic_info['state']

        if state == "off":
            return SonoffSwitch.SWITCH_STATE_OFF
        elif state == "on":
            return SonoffSwitch.SWITCH_STATE_ON
        else:
            _LOGGER.warning("Unknown state %s returned.", state)
            return SonoffSwitch.SWITCH_STATE_UNKNOWN

    @state.setter
    def state(self, value: str):
        """
        Set the new switch state

        :param value: one of
                    SWITCH_STATE_ON
                    SWITCH_STATE_OFF
        :raises ValueError: on invalid state
        :raises SonoffDeviceException: on error

        """
        if not isinstance(value, str):
            raise ValueError("State must be str, not of %s.", type(value))
        elif value.upper() == SonoffSwitch.SWITCH_STATE_ON:
            self.turn_on()
        elif value.upper() == SonoffSwitch.SWITCH_STATE_OFF:
            self.turn_off()
        else:
            raise ValueError("State %s is not valid.", value)

    @property
    def is_on(self) -> bool:
        """
        Returns whether device is on.

        :return: True if device is on, False otherwise
        """
        return self.basic_info['state'] == "on"

    def turn_on(self):
        """
        Turn the switch on.

        :raises SonoffDeviceException: on error
        """
        self._update_helper(self.client.get_update_payload(self.device_id, {"switch": "on"}))

    def turn_off(self):
        """
        Turn the switch off.

        :raises SonoffDeviceException: on error
        """
        self._update_helper(self.client.get_update_payload(self.device_id, {"switch": "off"}))
