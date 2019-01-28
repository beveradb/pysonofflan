import asyncio
import sys
import click
import logging

if sys.version_info < (3, 5):
    print("To use this script you need python 3.5 or newer! got %s" %
          sys.version_info)
    sys.exit(1)

from pysonofflan import (SonoffSwitch, Discover)

pass_sonoff_switch = click.make_pass_decorator(SonoffSwitch)


@click.group(invoke_without_command=True)
@click.option('--host', envvar="PYSONOFFLAN_HOST", required=False,
              help='The host name or IP address of the device to connect to.')
@click.option('--device_id', envvar="PYSONOFFLAN_device_id", required=False,
              help='The device ID of the device to connect to.')
@click.option('--debug/--normal', default=False)
@click.pass_context
def cli(ctx, host, device_id, debug):
    """A cli tool for controlling Sonoff Smart Switches/Plugs (Basic/S20/Touch) in LAN Mode."""
    if debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    if ctx.invoked_subcommand == "discover":
        return

    if device_id is not None and host is None:
        click.echo("Device ID is given, using discovery to find host %s" % device_id)
        host = find_host_from_device_id(device_id=device_id)
        if host:
            click.echo("Matching Device ID found! IP: %s" % host)
        else:
            click.echo("No device with name %s found" % device_id)
            return

    if host is None:
        click.echo("No host name given - try discovery mode to find your device!")
        sys.exit(1)

    click.echo("Initialising SonoffSwitch with host %s" % host)
    ctx.obj = SonoffSwitch(host)

    if ctx.invoked_subcommand == "state":
        return

    ctx.invoke(state)


@cli.command()
def discover():
    """Discover devices in the network."""
    click.echo("Attempting to discover Sonoff LAN Mode devices on the local network, please wait...")
    found_devs = asyncio.get_event_loop().run_until_complete(Discover.discover()).items()
    for ip, found_device_id in found_devs:
        click.echo("Found Sonoff LAN Mode device at IP %s with ID: %s" % (ip, found_device_id))

    return found_devs


def find_host_from_device_id(device_id):
    """Discover a device identified by its device_id"""
    click.echo("Trying to discover %s by scanning for devices on local network, please wait..." % device_id)
    found_devs = asyncio.get_event_loop().run_until_complete(Discover.discover()).items()
    for ip, found_device_id in found_devs:
        click.echo("Found Sonoff LAN Mode device at IP %s with ID: %s" % (ip, found_device_id))
        if found_device_id.lower() == device_id.lower():
            return ip
    return None


@cli.command()
@pass_sonoff_switch
def state(device: SonoffSwitch):
    """Print out device ID and state."""

    try:
        device_id = asyncio.get_event_loop().run_until_complete(device.device_id)
    except Exception as ex:
        click.echo("Error getting device ID: %s" % ex)
        return None

    click.echo(
        click.style("== Device: %s ==" % device_id, bold=True)
    )

    is_on = asyncio.get_event_loop().run_until_complete(device.is_on)
    click.echo("State: " + click.style("ON" if is_on else "OFF",
                                       fg="green" if is_on else "red"))
    click.echo("Host/IP: %s" % device.host)


@cli.command()
@pass_sonoff_switch
def on(device: SonoffSwitch, index):
    """Turn the device on."""
    click.echo("Turning on..")
    if index is None:
        asyncio.get_event_loop().run_until_complete(device.turn_on())
    else:
        asyncio.get_event_loop().run_until_complete(device.turn_on())


@cli.command()
@pass_sonoff_switch
async def off(device: SonoffSwitch, index):
    """Turn the device off."""
    click.echo("Turning off..")
    if index is None:
        asyncio.get_event_loop().run_until_complete(device.turn_off())
    else:
        asyncio.get_event_loop().run_until_complete(device.turn_off())


if __name__ == "__main__":
    cli()
