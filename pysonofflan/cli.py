import asyncio
import logging
import sys

import click
import click_log
from click_log import ClickHandler

from pysonofflan import (SonoffSwitch, Discover)

if sys.version_info < (3, 5):
    print("To use this script you need python 3.5 or newer! got %s" %
          sys.version_info)
    sys.exit(1)


class CustomColorFormatter(click_log.ColorFormatter):
    colors = {
        'error': dict(fg='red'),
        'exception': dict(fg='red'),
        'critical': dict(fg='red'),
        'info': dict(fg='bright_green'),
        'debug': dict(fg='blue'),
        'warning': dict(fg='yellow')
    }

    def format(self, record):
        if not record.exc_info:
            level = record.levelname.lower()
            msg = record.getMessage()

            prefix = self.formatTime(record, self.datefmt) + " - "
            if level in self.colors:
                prefix += click.style('{}: '.format(level),
                                      **self.colors[level])

            msg = '\n'.join(prefix + x for x in msg.splitlines())
            return msg
        return logging.Formatter.format(self, record)


logger = logging.getLogger(__name__)
click_log.basic_config(logger)

_default_handler = ClickHandler()
_default_handler.formatter = CustomColorFormatter()

logger.handlers = [_default_handler]

pass_config = click.make_pass_decorator(dict, ensure=True)


@click.group(invoke_without_command=True)
@click.option('--host', envvar="PYSONOFFLAN_HOST", required=False,
              help='IP address or hostname of the device to connect to.')
@click.option('--device_id', envvar="PYSONOFFLAN_device_id", required=False,
              help='Device ID of the device to connect to.')
@click.option('--inching', envvar="PYSONOFFLAN_inching", required=False,
              help='Number of seconds of "on" time if this is an '
                   'Inching/Momentary switch.')
@click.pass_context
@click_log.simple_verbosity_option(logger, '--loglevel', '-l')
@click.version_option()
def cli(ctx, host, device_id, inching):
    """A cli tool for controlling Sonoff Smart Switches/Plugs in LAN Mode."""
    if ctx.invoked_subcommand == "discover":
        return

    if device_id is not None and host is None:
        logger.info(
            "Device ID is given, using discovery to find host %s" % device_id)
        host = find_host_from_device_id(device_id=device_id)
        if host:
            logger.info("Matching Device ID found! IP: %s" % host)
        else:
            logger.info("No device with name %s found" % device_id)
            return

    if host is None:
        logger.error("No host name given, see usage below:")
        click.echo(ctx.get_help())
        sys.exit(1)

    ctx.obj = {"host": host, "inching": inching}


@cli.command()
@click.option('--network', default=None, help='Network address to scan, ex: 192.168.0.0/24')
def discover(network):
    """Discover devices in the network (takes ~1 minute)."""
    logger.info(
        "Attempting to discover Sonoff LAN Mode devices "
        "on the local network, please wait..."
    )
    found_devices = asyncio.get_event_loop().run_until_complete(
        Discover.discover(logger, network)).items()
    for ip, found_device_id in found_devices:
        logger.info("Found Sonoff LAN Mode device at IP %s" % ip)

    return found_devices


def find_host_from_device_id(device_id):
    """Discover a device identified by its device_id"""
    logger.info(
        "Trying to discover %s by scanning for devices "
        "on local network, please wait..." % device_id)
    found_devices = asyncio.get_event_loop().run_until_complete(
        Discover.discover(logger)).items()
    for ip, _ in found_devices:
        logger.info("Found Sonoff LAN Mode device at IP %s, attempting to "
                    "read state to get device ID" % ip)

        shared_state = {'device_id_at_current_ip': None}

        async def device_id_callback(device: SonoffSwitch):
            if device.basic_info is not None:
                device.shared_state['device_id_at_current_ip'] = \
                    device.device_id
                device.shutdown_event_loop()

        SonoffSwitch(
            host=ip,
            callback_after_update=device_id_callback,
            shared_state=shared_state,
            logger=logger
        )

        current_device_id = shared_state['device_id_at_current_ip']

        if device_id.lower() == current_device_id.lower():
            return ip
        else:
            logger.info(
                "Found device ID %s which did not match" % current_device_id
            )
    return None


@cli.command()
@pass_config
def state(config: dict):
    """Connect to device and print current state."""

    async def state_callback(device):
        if device.basic_info is not None:
            if device.available:
                print_device_details(device)

                device.shutdown_event_loop()

    logger.info("Initialising SonoffSwitch with host %s" % config['host'])
    SonoffSwitch(
        host=config['host'],
        callback_after_update=state_callback,
        logger=logger
    )


@cli.command()
@pass_config
def on(config: dict):
    """Turn the device on."""
    switch_device(config['host'], config['inching'], 'on')


@cli.command()
@pass_config
def off(config: dict):
    """Turn the device off."""
    switch_device(config['host'], config['inching'], 'off')


@cli.command()
@pass_config
def listen(config: dict):
    """Connect to device, print state, then print updates until quit."""

    async def state_callback(self):
        if self.basic_info is not None:
            print_device_details(self)

            if self.shared_state['callback_counter'] == 0:
                logger.info(
                    "Listening for updates forever... Press CTRL+C to quit.")

        self.shared_state['callback_counter'] += 1

    logger.info("Initialising SonoffSwitch with host %s" % config['host'])

    shared_state = {'callback_counter': 0}
    SonoffSwitch(
        host=config['host'],
        callback_after_update=state_callback,
        shared_state=shared_state,
        logger=logger
    )


def print_device_details(device):
    if device.basic_info is not None:
        device_id = device.device_id

        logger.info(
            click.style("== Device: %s (%s) ==" % (device_id, device.host),
                        bold=True)
        )

        logger.info("State: " + click.style(
            "ON" if device.is_on else "OFF",
            fg="green" if device.is_on else "red")
                    )


def switch_device(host, inching, new_state):
    logger.info("Initialising SonoffSwitch with host %s" % host)

    async def update_callback(device: SonoffSwitch):
        if device.basic_info is not None:

            if device.available:

                if inching is None:
                    print_device_details(device)

                    if device.is_on:
                        if new_state == "on":
                            device.shutdown_event_loop()
                        else:
                            await device.turn_off()
                            
                    elif device.is_off:
                        if new_state == "off":
                            device.shutdown_event_loop()
                        else:
                            await device.turn_on()

                else:
                    logger.info("Inching device activated by switching ON for "
                                "%ss" % inching)

    SonoffSwitch(
        host=host,
        callback_after_update=update_callback,
        inching_seconds=int(inching) if inching else None,
        logger=logger
    )


if __name__ == "__main__":
    cli()
