#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `pysonofflan` package."""
import unittest
from click.testing import CliRunner
from pysonofflan import cli
from tests.sonoff_mock import start_device, stop_device

class TestCLI(unittest.TestCase):
    """Tests for pysonofflan CLI interface."""

    def setUp(self):
        """Set up test fixtures, if any."""

    def tearDown(self):
        """Tear down test fixtures, if any."""

    def test_cli_no_args(self):
        """Test the CLI."""
        runner = CliRunner()
        result = runner.invoke(cli.cli)
        assert 'No host name or device_id given, see usage below' in result.output
        assert 'Commands:' in result.output

    def test_cli_invalid_arg(self):
        """Test the CLI."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ['hello'])
        assert 'Error: No such command "hello"' in result.output

    def test_cli_help(self):
        runner = CliRunner()
        result = runner.invoke(cli.cli, ['--help']) 
        assert result.exit_code == 0
        assert 'Show this message and exit.' in result.output

    def test_cli_version(self):
        runner = CliRunner()
        result = runner.invoke(cli.cli, ['--version'])
        assert result.exit_code == 0
        assert ', version' in result.output

    def test_cli_no_device_id(self):
        """Test the CLI."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ['--device_id'])
        assert 'Error: --device_id option requires an argument' in \
               result.output
               
    def test_cli_no_host_id(self):
        """Test the CLI."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ['--host'])
        assert 'Error: --host option requires an argument' in \
               result.output

    def test_cli_state(self):
        """Test the CLI."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ['state'])
        assert 'No host name or device_id given, see usage below' in result.output

    def test_cli_on(self):

        start_device("PlugOn", "plug")

        """Test the CLI."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ['--device_id', 'PlugOnMock', 'on'])

        print(result.output)
        
        assert 'info: State: ON' in result.output

        stop_device()

    def test_cli_off(self):

        start_device("PlugOff", "plug")

        """Test the CLI."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ['--device_id', 'PlugOffMock', 'off'])

        print(result.output)

        assert 'info: State: OFF' in result.output

        stop_device()        

    def test_cli_on_strip(self):

        start_device("StripOn", "strip")

        """Test the CLI."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ['--device_id', 'StripOnMock', 'on'])

        print(result.output)

        assert 'info: State: ON' in result.output

        stop_device()

    def test_cli_off_strip(self):

        start_device("StripOff", "strip")

        """Test the CLI."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ['--device_id', 'StripOffMock', 'on'])

        print(result.output)

        assert 'info: State: OFF' in result.output

        stop_device()

    def test_cli_on_encrypt(self):

        start_device("PlugEncrypt", "plug")

        """Test the CLI."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ['--device_id', 'PlugEncryptMock', '--api_key', 'testkey', 'on'])

        print(result.output)

        assert 'info: State: ON' in result.output

    def test_cli_on_strip_encrypt(self):

        start_device("StripEncrypt", "strip")

        """Test the CLI."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ['--device_id', 'StripEncryptMock', '--api_key', 'testkey', 'on'])

        print(result.output)

        assert 'info: State: ON' in result.output

        stop_device()

    def test_cli_discover(self):   

        start_device("DiscoverDevice", "plug")

        """Test the CLI."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ['discover'])
        
        print(result.output)

        assert "Attempting to discover Sonoff LAN Mode devices on the local " \
               "network" in result.output
        assert "DiscoverDevice" in result.output     

        stop_device()

    def test_cli_discover_debug(self):
        """Test the CLI."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ['-l', 'DEBUG', 'discover'])
        assert "Looking for all eWeLink devices on local network" in \
               result.output

if __name__ == '__main__':
    unittest.main()