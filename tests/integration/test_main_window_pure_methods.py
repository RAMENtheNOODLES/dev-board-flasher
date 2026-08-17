"""Targeted tests for a couple of main.MainWindow's pure-branching methods.

MainWindow.__init__ runs full real app startup (settings, board discovery,
serial port enumeration, background workers, a GitHub update check) with no
dependency-injection seams, so constructing a real instance is out of scope
here (see the test suite plan). Instead these call the methods unbound
against a minimal stub `self` exposing just the attributes each one actually
touches - proving out the branching logic without paying for real startup.
"""

import logging

import pytest
from PySide6.QtSerialPort import QSerialPort

from main import MainWindow

pytestmark = pytest.mark.integration


class _StubWidget:
	def __init__(self, text=""):
		self._text = text
		self.enabled = None

	def text(self):
		return self._text

	def setEnabled(self, enabled):
		self.enabled = enabled


class _StubSerial:
	def __init__(self, is_open=False):
		self._is_open = is_open

	def isOpen(self):
		return self._is_open


def test_check_can_upload_false_when_no_file_selected():
	stub = type("StubSelf", (), {})()
	stub.fileName = _StubWidget(text="")
	stub.serial = _StubSerial(is_open=False)
	stub.uploadBoardButton = _StubWidget()

	assert MainWindow.check_can_upload(stub) is False
	assert stub.uploadBoardButton.enabled is False


def test_check_can_upload_false_when_serial_monitor_is_open():
	stub = type("StubSelf", (), {})()
	stub.fileName = _StubWidget(text="firmware.hex")
	stub.serial = _StubSerial(is_open=True)
	stub.uploadBoardButton = _StubWidget()

	assert MainWindow.check_can_upload(stub) is False
	assert stub.uploadBoardButton.enabled is False


def test_check_can_upload_true_when_file_selected_and_serial_closed():
	stub = type("StubSelf", (), {})()
	stub.fileName = _StubWidget(text="firmware.hex")
	stub.serial = _StubSerial(is_open=False)
	stub.uploadBoardButton = _StubWidget()

	assert MainWindow.check_can_upload(stub) is True
	assert stub.uploadBoardButton.enabled is True


class _StubMainWindowForSerialError:
	def __init__(self):
		self.logger = logging.getLogger("test")
		self.toggle_connection_calls = 0

	def toggle_connection(self):
		self.toggle_connection_calls += 1


@pytest.mark.parametrize(
	"error",
	[QSerialPort.SerialPortError.NotOpenError, QSerialPort.SerialPortError.NoError],
)
def test_handle_serial_error_ignores_benign_errors(error):
	stub = _StubMainWindowForSerialError()

	MainWindow.handle_serial_error(stub, error)

	assert stub.toggle_connection_calls == 0


def test_handle_serial_error_disconnects_on_resource_error():
	stub = _StubMainWindowForSerialError()

	MainWindow.handle_serial_error(stub, QSerialPort.SerialPortError.ResourceError)

	assert stub.toggle_connection_calls == 1


def test_handle_serial_error_disconnects_on_other_unexpected_errors():
	stub = _StubMainWindowForSerialError()

	MainWindow.handle_serial_error(stub, QSerialPort.SerialPortError.WriteError)

	assert stub.toggle_connection_calls == 1
