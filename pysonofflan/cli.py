import asyncio
import logging
import sys

import click

from pysonofflan import (SonoffSwitch, Discover)

if sys.version_info < (3, 5):
    print("To use this script you need python 3.5 or newer! got %s" %
          sys.version_info)
    sys.exit(1)

pass_host = click.make_pass_decorator(str)


@click.group(invoke_without_command=True)
@click.option('--host', envvar="PYSONOFFLAN_HOST", required=False,
              help='The host name or IP address of the device to connect to.')
@click.option('--device_id', envvar="PYSONOFFLAN_device_id", required=False,
              help='The device ID of the device to connect to.')
@click.option('--debug/--normal', default=False)
@click.pass_context
def cli(ctx, host, device_id, debug):
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

    ctx.obj = host


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
@pass_host
def state(host: str):
    """Print out device ID and state."""

    click.echo("Initialising SonoffSwitch with host %s" % host)
    device = SonoffSwitch(host, end_after_first_update=True)
    print_device_details(device)


def print_device_details(device):
    if device.basic_info is not None:
        device_id = device.device_id

        click.echo(
            click.style("== Device: %s ==" % device_id, bold=True)
        )

        click.echo("State: " + click.style("ON" if device.is_on else "OFF",
                                           fg="green" if device.is_on else "red"))
        click.echo("Host/IP: %s" % device.host)


@cli.command()
@pass_host
def on(host: str):
    """Turn the device on."""

    async def turn_on_callback(device):
        click.echo("Initial state:")

        if device.basic_info is not None:
            print_device_details(device)

            device.client.keep_running = False
            device.turn_on()

            click.echo("New state:")
            print_device_details(device)

    click.echo("Initialising SonoffSwitch with host %s" % host)
    SonoffSwitch(
        host=host,
        callback_after_update=turn_on_callback,
        ping_interval=60
    )


@cli.command()
@pass_host
def off(host: str):
    """Turn the device on."""

    async def turn_off_callback(device):
        click.echo("Initial state:")

        if device.basic_info is not None:
            print_device_details(device)

            device.client.keep_running = False
            device.turn_off()

            click.echo("New state:")
            print_device_details(device)

    click.echo("Initialising SonoffSwitch with host %s" % host)
    SonoffSwitch(
        host=host,
        callback_after_update=turn_off_callback,
        ping_interval=60
    )


if __name__ == "__main__":
    cli()
