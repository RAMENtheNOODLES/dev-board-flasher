import logging
from types import SimpleNamespace

import pytest

import tools.can as can_module


class _FakeSignal:
	def __init__(self, name, unit=""):
		self.name = name
		self.unit = unit


class _FakeMessage:
	def __init__(self, id, name, signals):
		self.id = id
		self.name = name
		self._signals = signals

	def signals(self):
		return self._signals


class _FakeDbc:
	def __init__(self, messages):
		self._messages = messages

	def messages(self):
		return self._messages


def _make_can() -> can_module.CAN:
	"""Builds a bare CAN instance without running __init__.

	CAN.__init__ needs a real canlib.Device and, unless an explicit bitrate
	is passed, calls the DLL-loading _canlib_can() itself - overkill for
	tests that only exercise a single method operating on self._dbc/
	self._channel. Callers set whatever attributes their target method
	actually touches.
	"""
	return can_module.CAN.__new__(can_module.CAN)


def test_dbc_message_signals_returns_empty_dict_without_a_loaded_dbc():
	can = _make_can()
	can._dbc = None

	assert can.dbc_message_signals() == {}


def test_dbc_message_signals_strips_the_extended_id_marker_bit(monkeypatch):
	"""Regression test.

	kvadblib.Message.id sets bit 31 (MessageFlag.EXT) to mark an extended
	(29-bit) CAN id, but a received Frame's raw .id never carries that bit -
	its extended-ness lives in .flags instead. Before this was fixed,
	dbc_message_signals() handed back keys with that bit still set, so every
	extended-id DBC message silently never matched incoming frames in
	update_tree(): every frame for a message that should have been
	recognized was instead treated as unknown and added as a new "unknown
	id" row, and the actual DBC-known row just sat frozen forever.
	"""
	ext_flag = 0x80000000
	monkeypatch.setattr(
		can_module, "_kvadblib", lambda: SimpleNamespace(MessageFlag=SimpleNamespace(EXT=ext_flag))
	)

	extended_message = _FakeMessage(
		id=0x80001234, name="ExtendedMessage", signals=[_FakeSignal("EngineSpeed", "rpm")]
	)
	standard_message = _FakeMessage(id=0x123, name="StandardMessage", signals=[])

	can = _make_can()
	can._dbc = _FakeDbc([extended_message, standard_message])

	result = can.dbc_message_signals()

	assert 0x80001234 not in result
	assert result[0x1234] == ("ExtendedMessage", [("EngineSpeed", "rpm")])
	assert result[0x123] == ("StandardMessage", [])


def test_receive_filters_out_bus_error_frames(monkeypatch):
	"""Regression test.

	The Kvaser driver synthesizes an "error frame" (typically id 0x0) through
	the same channel.read() call, instead of a real frame, when the channel
	can't successfully read anything off the wire - most commonly a bitrate
	mismatch with the actual bus. Before this was fixed, receive() passed
	these straight through as if they were real bus traffic: the CAN Viewer
	tree showed nothing but an endlessly repeating fake "0x0" message, while
	genuine traffic (received by other tools using the correct bitrate) was
	silently never reaching this app at all.
	"""
	error_frame_flag = 0x20

	class _FakeCanNoMsg(Exception):
		pass

	monkeypatch.setattr(
		can_module,
		"_canlib_can",
		lambda: SimpleNamespace(
			MessageFlag=SimpleNamespace(ERROR_FRAME=error_frame_flag),
			CanNoMsg=_FakeCanNoMsg,
		),
	)

	error_frame = SimpleNamespace(id=0x0, dlc=4, flags=error_frame_flag)
	real_frame = SimpleNamespace(id=0x100, dlc=8, flags=0)

	class _FakeChannel:
		def __init__(self, frames):
			self._frames = list(frames)

		def read(self, timeout):
			return self._frames.pop(0)

	can = _make_can()
	can.logger = logging.getLogger("test")
	can.bitrate = "500K"
	can._warned_about_errors = False
	can._channel = _FakeChannel([error_frame, real_frame])

	# The error frame is swallowed like a timeout, not surfaced as a message.
	assert can.receive() is None
	assert can._warned_about_errors is True

	# A genuine frame right after still passes through unchanged.
	assert can.receive() is real_frame


def test_bus_load_converts_the_raw_0_10000_statistics_value_to_a_percentage():
	class _FakeStatistics:
		busLoad = 4250  # 42.50%

	class _FakeChannel:
		def get_bus_statistics(self):
			return _FakeStatistics()

	can = _make_can()
	can._channel = _FakeChannel()

	assert can.bus_load() == 42.5


def test_bus_load_raises_when_the_channel_is_not_open():
	can = _make_can()
	can._channel = None

	with pytest.raises(RuntimeError):
		can.bus_load()
