import asyncio
import sys
import click
import logging

if sys.version_info < (3, 5):
    print("To use this script you need python 3.5 or newer! got %s" %
          sys.version_info)
    sys.exit(1)

from pysonofflan import (SonoffDevice,
                         SonoffSwitch,
                         Discover)  # noqa: E402

pass_dev = click.make_pass_decorator(SonoffDevice)


@click.group(invoke_without_command=True)
@click.option('--host', envvar="PYSONOFFLAN_HOST", required=False,
              help='The host name or IP address of the device to connect to.')
@click.option('--device_id', envvar="PYSONOFFLAN_device_id", required=False,
              help='The device ID of the device to connect to.')
@click.option('--debug/--normal', default=False)
@click.option('--switch', default=False, is_flag=True)
@click.pass_context
def cli(ctx, host, device_id, debug, switch):
    """A cli tool for controlling Sonoff Smart Switches/Plugs (Basic/S20/Touch) in LAN Mode."""
    if debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    if ctx.invoked_subcommand == "discover":
        return

    if device_id is not None and host is None:
        click.echo("Device ID is given, using discovery to find host %s" %
                   device_id)
        host = find_host_from_device_id(device_id=device_id)
        if host:
            click.echo("Found hostname is {}".format(host))
        else:
            click.echo("No device with name {} found".format(device_id))
            return

    if host is None:
        click.echo("No host name given, trying discovery..")
        ctx.invoke(discover)
        return
    else:
        if not switch:
            click.echo("No --switch given, discovering..")
            dev = asyncio.get_event_loop().run_until_complete(Discover.discover_single(host))
        elif switch:
            dev = SonoffSwitch(host)
        else:
            click.echo(
                "Unable to detect type, use --switch!")
            return
        ctx.obj = dev

    if ctx.invoked_subcommand is None:
        ctx.invoke(state)


@cli.command()
@click.option('--timeout', default=3, required=False)
@click.option('--discover-only', default=False)
@click.pass_context
async def discover(ctx, timeout, discover_only):
    """Discover devices in the network."""
    click.echo("Discovering devices for %s seconds" % timeout)
    found_devs = (await Discover.discover()).items()
    if not discover_only:
        for ip, dev in found_devs:
            ctx.obj = dev
            ctx.invoke(state)
            print()

    return found_devs


async def find_host_from_device_id(device_id, timeout=1, attempts=3):
    """Discover a device identified by its device_id"""
    click.echo("Trying to discover %s using %s attempts of %s seconds" %
               (device_id, attempts, timeout))
    for attempt in range(1, attempts):
        click.echo("Attempt %s of %s" % (attempt, attempts))
        found_devs = (await Discover.discover()).items()
        for host, found_device_id in found_devs:
            if found_device_id.lower() == device_id.lower():
                return host
    return None


@cli.command()
@pass_dev
@click.pass_context
async def state(ctx, dev):
    """Print out device ID and state."""
    click.echo(click.style("== %s ==" % (await dev.device_id), bold=True))

    click.echo(click.style("Device state: %s" % "ON" if dev.is_on else "OFF",
                           fg="green" if dev.is_on else "red"))
    click.echo("Host/IP: %s" % dev.host)


@cli.command()
@click.argument('index', type=int, required=False)
@pass_dev
async def on(switch, index):
    """Turn the device on."""
    click.echo("Turning on..")
    if index is None:
        switch.turn_on()
    else:
        switch.turn_on(index=(index - 1))


@cli.command()
@click.argument('index', type=int, required=False)
@pass_dev
async def off(switch, index):
    """Turn the device off."""
    click.echo("Turning off..")
    if index is None:
        switch.turn_off()
    else:
        switch.turn_off(index=(index - 1))


if __name__ == "__main__":
    cli()
