#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `pysonofflan` package."""

import unittest
from click.testing import CliRunner

from pysonofflan import cli


class TestPysonofflan(unittest.TestCase):
    """Tests for `pysonofflan` package."""

    def setUp(self):
        """Set up test fixtures, if any."""

    def tearDown(self):
        """Tear down test fixtures, if any."""

    def test_cli_no_args(self):
        """Test the CLI."""
        runner = CliRunner()
        result = runner.invoke(cli.cli)
        assert 'No host name given - try discovery mode' in result.output

    def test_cli_invalid_arg(self):
        """Test the CLI."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ['hello'])
        assert 'Error: No such command "hello"' in result.output

    def test_cli_help(self):
        runner = CliRunner()
        help_result = runner.invoke(cli.cli, ['--help'])
        assert help_result.exit_code == 0
        assert 'Show this message and exit.' in help_result.output

    def test_cli_discovery(self):
        """Test the CLI."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ['discover'])
        assert result.exit_code == 0
        assert 'Attempting to discover' in result.output

    def test_cli_no_device_id(self):
        """Test the CLI."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ['--device_id'])
        assert 'Error: --device_id option requires an argument' in result.output

    def test_cli_with_device_id(self):
        """Test the CLI."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ['--device_id', '100060af40'])
        assert 'Trying to discover 100060af40 by scanning for devices on local network' in result.output

    def test_cli_state(self):
        """Test the CLI."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ['state'])
        assert 'No host name given' in result.output

    def test_debug_flag(self):
        """Test the CLI."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ['--debug', 'discover'])
        assert 'Attempting to discover Sonoff LAN Mode devices' in result.output

    def test_unconnectable_host_state(self):
        """Test the CLI."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ['--host', '127.0.0.100', 'state'])
        assert 'Error getting device ID: Unable to connect to Sonoff' in result.output
