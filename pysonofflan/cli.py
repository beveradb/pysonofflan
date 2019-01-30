import asyncio
import logging
import sys

import click

from pysonofflan import (SonoffSwitch, Discover)

if sys.version_info < (3, 5):
    print("To use this script you need python 3.5 or newer! got %s" %
          sys.version_info)
    sys.exit(1)

pass_config = click.make_pass_decorator(dict, ensure=True)


@click.group(invoke_without_command=True)
@click.option('--host', envvar="PYSONOFFLAN_HOST", required=False,
              help='The host name or IP address of the device to connect to.')
@click.option('--device_id', envvar="PYSONOFFLAN_device_id", required=False,
              help='The device ID of the device to connect to.')
@click.option('--inching', envvar="PYSONOFFLAN_inching", required=False,
              help='Number of seconds of "on" time if this is an '
                   'Inching/Momentary switch.')
@click.option('--debug/--normal', default=False)
@click.pass_context
def cli(ctx, host, device_id, inching, debug):
    """A cli tool for controlling Sonoff Smart Switches/Plugs
    (Basic/S20/Touch) in LAN Mode."""
    if debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    if ctx.invoked_subcommand == "discover":
        return

    if device_id is not None and host is None:
        click.echo(
            "Device ID is given, using discovery to find host %s" % device_id)
        host = find_host_from_device_id(device_id=device_id)
        if host:
            click.echo("Matching Device ID found! IP: %s" % host)
        else:
            click.echo("No device with name %s found" % device_id)
            return

    if host is None:
        click.echo(
            "No host name given - try discovery mode to find your device!")
        sys.exit(1)

    ctx.obj = {"host": host, "inching": inching}


@cli.command()
def discover():
    """Discover devices in the network."""
    click.echo(
        "Attempting to discover Sonoff LAN Mode devices "
        "on the local network, please wait..."
    )
    found_devices = asyncio.get_event_loop().run_until_complete(
        Discover.discover()).items()
    for ip, found_device_id in found_devices:
        click.echo("Found Sonoff LAN Mode device at IP %s with ID: %s" % (
            ip, found_device_id))

    return found_devices


def find_host_from_device_id(device_id):
    """Discover a device identified by its device_id"""
    click.echo(
        "Trying to discover %s by scanning for devices "
        "on local network, please wait..." % device_id)
    found_devices = asyncio.get_event_loop().run_until_complete(
        Discover.discover()).items()
    for ip, found_device_id in found_devices:
        click.echo("Found Sonoff LAN Mode device at IP %s with ID: %s"
                   % (ip, found_device_id))
        if found_device_id.lower() == device_id.lower():
            return ip
    return None


@cli.command()
@pass_config
def state(config: dict):
    """Connect to device, print out device ID and state, then keep connected
    to the device to print any status updates from the device itself"""

    async def state_callback(device):
        if device.basic_info is not None:
            print_device_details(device)

            device.shutdown_event_loop()

    click.echo("Initialising SonoffSwitch with host %s" % config['host'])
    SonoffSwitch(
        host=config['host'],
        callback_after_update=state_callback
    )


@cli.command()
@pass_config
def listen(config: dict):
    """Print out device ID and state."""

    async def state_callback(self):
        if self.basic_info is not None:
            print_device_details(self)

            if self.shared_state['callback_counter'] == 0:
                click.echo(
                    "Listening for updates forever... Press CTRL+C to quit.")

        self.shared_state['callback_counter'] += 1

    click.echo("Initialising SonoffSwitch with host %s" % config['host'])

    shared_state = {'callback_counter': 0}
    SonoffSwitch(
        host=config['host'],
        callback_after_update=state_callback,
        shared_state=shared_state
    )


def print_device_details(device):
    if device.basic_info is not None:
        device_id = device.device_id

        click.echo(
            click.style("== Device: %s (%s) ==" % (device_id, device.host),
                        bold=True)
        )

        click.echo("State: " + click.style(
            "ON" if device.is_on else "OFF",
            fg="green" if device.is_on else "red")
                   )


def switch_device(host, inching, new_state):
    click.echo("Initialising SonoffSwitch with host %s" % host)

    async def update_callback(device: SonoffSwitch):
        if device.basic_info is not None:
            if inching is None:
                click.echo("Initial state:")
                print_device_details(device)

                device.client.keep_running = False
                if new_state == "on":
                    await device.turn_on()
                else:
                    await device.turn_off()
            else:
                click.echo("Inching device activated by switching ON for "
                           "%ss" % inching)

            click.echo("New state:")
            print_device_details(device)

    SonoffSwitch(
        host=host,
        callback_after_update=update_callback,
        inching_seconds=int(inching) if inching else None
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


if __name__ == "__main__":
    cli()
