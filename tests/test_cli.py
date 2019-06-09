#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `pysonofflan` package."""

import unittest

from click.testing import CliRunner

from pysonofflan import cli


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
        assert 'No host name given, see usage below' in result.output
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
        assert 'No host name given, see usage below' in result.output

    def test_cli_discover(self):
        """Test the CLI."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ['discover'])
        assert "Attempting to discover Sonoff LAN Mode devices on the local " \
               "network" in result.output

    def test_cli_discover_debug(self):
        """Test the CLI."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ['-l', 'DEBUG', 'discover'])
        assert "Attempting connection to IP: 192.168.0.1 on port 8081" in \
               result.output
