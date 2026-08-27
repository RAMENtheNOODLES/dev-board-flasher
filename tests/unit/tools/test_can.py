import logging
from types import SimpleNamespace

import pytest

import tools.can as can_module


class _FakeSignal:
	def __init__(self, name, unit="", enums=None):
		self.name = name
		self.unit = unit
		# Real (kvadblib) non-enum Signal objects have no `enums` attribute at
		# all - only EnumSignal does - so this is left unset rather than `{}`
		# unless a caller actually wants an enum signal, matching BoundSignal.is_enum's
		# `hasattr(self.signal, 'enums')` check.
		if enums is not None:
			self.enums = enums


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


class _FakeBoundSignal:
	def __init__(self, signal, phys):
		self.signal = signal
		self.name = signal.name
		self.unit = signal.unit
		self.phys = phys

	@property
	def is_enum(self):
		return hasattr(self.signal, "enums")


class _FakeTxMessage(_FakeMessage):
	"""Extends `_FakeMessage` with `asframe`/`bind`, as needed by `CAN.dbc_tx_messages`."""

	def __init__(self, id, name, signals, default_values=None):
		super().__init__(id, name, signals)
		self._default_values = default_values or {}

	def asframe(self):
		return object()  # opaque - bind() below never touches it

	def bind(self, frame):
		return [_FakeBoundSignal(s, self._default_values.get(s.name, 0.0)) for s in self._signals]


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


def test_dbc_tx_messages_returns_empty_list_without_a_loaded_dbc():
	can = _make_can()
	can._dbc = None

	assert can.dbc_tx_messages() == []


def test_dbc_tx_messages_includes_the_j1939_pgn_and_each_signals_default_value(monkeypatch):
	ext_flag = 0x80000000
	monkeypatch.setattr(
		can_module, "_kvadblib", lambda: SimpleNamespace(MessageFlag=SimpleNamespace(EXT=ext_flag))
	)

	# PDU2-format id (PF=0xFE >= 240): PGN = (pf << 8) + ps = 0xFECA.
	msg = _FakeTxMessage(
		id=ext_flag | 0x18FECA00,
		name="EngineTemp1",
		signals=[_FakeSignal("CoolantTemp", "C")],
		default_values={"CoolantTemp": -40.0},
	)
	can = _make_can()
	can._dbc = _FakeDbc([msg])

	result = can.dbc_tx_messages()

	assert len(result) == 1
	info = result[0]
	assert info.name == "EngineTemp1"
	assert info.pgn == 0xFECA
	assert info.signals == (can_module.TxSignalInfo(name="CoolantTemp", unit="C", default_value=-40.0),)
	assert info.signals[0].enum_values == {}


def test_dbc_tx_messages_includes_the_value_table_for_an_enum_signal(monkeypatch):
	ext_flag = 0x80000000
	monkeypatch.setattr(
		can_module, "_kvadblib", lambda: SimpleNamespace(MessageFlag=SimpleNamespace(EXT=ext_flag))
	)

	msg = _FakeTxMessage(
		id=ext_flag | 0x18FECA00,
		name="EngineTemp1",
		signals=[_FakeSignal("FanStatus", enums={"Off": 0, "On": 1, "Error": 2})],
		default_values={"FanStatus": 0.0},
	)
	can = _make_can()
	can._dbc = _FakeDbc([msg])

	result = can.dbc_tx_messages()

	assert result[0].signals[0].enum_values == {"Off": 0, "On": 1, "Error": 2}


def test_dbc_tx_messages_skips_a_message_kvadblib_cannot_build_a_default_frame_for(monkeypatch):
	"""Regression test.

	A message with, e.g., a DLC that doesn't fit the DBC's protocol makes
	kvadblib's Message.asframe()/bind() raise a KvdError - before this was
	handled, one such message in an otherwise-fine DBC crashed the whole TX
	Settings dialog instead of just being left out of the PGN picker.
	"""
	ext_flag = 0x80000000

	class _FakeKvdError(Exception):
		pass

	monkeypatch.setattr(
		can_module,
		"_kvadblib",
		lambda: SimpleNamespace(MessageFlag=SimpleNamespace(EXT=ext_flag), KvdError=_FakeKvdError),
	)

	class _BrokenMessage(_FakeTxMessage):
		def bind(self, frame):
			raise _FakeKvdError("One or more of the parameters in call is erronous (-3)")

	broken = _BrokenMessage(id=ext_flag | 0x18FECA00, name="Broken", signals=[_FakeSignal("Sig", "")])
	usable = _FakeTxMessage(
		id=ext_flag | 0x18F00400, name="EngineSpeed1", signals=[_FakeSignal("RPM", "rpm")]
	)
	can = _make_can()
	can.logger = logging.getLogger("test")
	can._dbc = _FakeDbc([broken, usable])

	result = can.dbc_tx_messages()

	assert [info.name for info in result] == ["EngineSpeed1"]


class _FakeSendMessage:
	"""Duck-typed stand-in for kvadblib.Message, as needed by CAN.send_message."""

	def __init__(self, signal_names, frame):
		self._signal_names = signal_names
		self._frame = frame
		#: The most recent bind() result, so a test can inspect what
		#: send_message() actually set on it.
		self.last_bound = None

	def asframe(self):
		return self._frame

	def bind(self, frame):
		bound = SimpleNamespace()
		for signal_name in self._signal_names:
			setattr(bound, signal_name, SimpleNamespace(phys=None))
		self.last_bound = bound
		return bound


class _FakeSendDbc:
	def __init__(self, message):
		self._message = message

	def get_message_by_name(self, name):
		return self._message


class _FakeSendChannel:
	def __init__(self):
		self.written = []

	def writeWait(self, frame, timeout):
		self.written.append(frame)


def test_send_message_writes_the_encoded_frame_and_returns_it():
	frame = SimpleNamespace(id=0x100, data=bytearray(8))
	message = _FakeSendMessage(["Sig1"], frame)
	channel = _FakeSendChannel()

	can = _make_can()
	can._dbc = _FakeSendDbc(message)
	can._channel = channel

	result = can.send_message("Msg1", Sig1=42.0)

	assert result is frame
	assert channel.written == [frame]


def test_send_message_sets_each_signals_phys_value():
	frame = SimpleNamespace(id=0x100, data=bytearray(8))
	message = _FakeSendMessage(["Sig1"], frame)
	can = _make_can()
	can._dbc = _FakeSendDbc(message)
	can._channel = _FakeSendChannel()

	can.send_message("Msg1", Sig1=42.0)

	assert message.last_bound.Sig1.phys == 42.0


def test_send_message_raises_when_the_channel_is_not_open():
	can = _make_can()
	can._channel = None
	can._dbc = _FakeSendDbc(_FakeSendMessage([], None))

	with pytest.raises(RuntimeError):
		can.send_message("Msg1")


def test_send_message_raises_when_no_dbc_is_loaded():
	can = _make_can()
	can._channel = _FakeSendChannel()
	can._dbc = None

	with pytest.raises(RuntimeError):
		can.send_message("Msg1")


def test_send_message_passes_the_timeout_through_to_writewait():
	"""send_message waits for the frame to actually go out (writeWait) rather than just queuing it (write) -
	with no other node on the bus to ACK, a fire-and-forget write() would let queued frames pile up behind
	the one stuck retrying until the driver's transmit buffer overflows."""
	frame = SimpleNamespace(id=0x100, data=bytearray(8))
	message = _FakeSendMessage(["Sig1"], frame)
	can = _make_can()
	can._dbc = _FakeSendDbc(message)

	class _TimeoutCapturingChannel:
		def writeWait(self, frame, timeout):
			self.timeout = timeout

	channel = _TimeoutCapturingChannel()
	can._channel = channel

	can.send_message("Msg1", Sig1=42.0, timeout=250)

	assert channel.timeout == 250


def test_send_writes_the_encoded_frame_with_a_timeout(monkeypatch):
	monkeypatch.setattr(can_module, "_canlib_can", lambda: _fake_ext_canlib_can(ext_flag=0x4))

	can = _make_can()
	channel = _FakeSendChannel()
	can._channel = channel

	can.send(frame_id=0x123, data=b"\x01\x02", extended=True, timeout=250)

	assert len(channel.written) == 1
	sent_frame = channel.written[0]
	assert sent_frame.id == 0x123
	assert bytes(sent_frame.data) == b"\x01\x02"
	assert sent_frame.flags == 0x4


def test_send_raises_when_the_channel_is_not_open():
	can = _make_can()
	can._channel = None

	with pytest.raises(RuntimeError):
		can.send(frame_id=0x123, data=b"\x00")


class _FakeInterpretSignal:
	def __init__(self, name, value, phys):
		self.name = name
		self.value = value
		self.phys = phys


def test_decode_returns_none_without_a_loaded_dbc():
	can = _make_can()
	can._dbc = None

	assert can.decode(SimpleNamespace()) is None


def test_decode_returns_none_when_the_frame_is_not_in_the_dbc(monkeypatch):
	class _FakeKvdNoMessage(Exception):
		pass

	monkeypatch.setattr(can_module, "_kvadblib", lambda: SimpleNamespace(KvdNoMessage=_FakeKvdNoMessage))

	class _RaisingDbc:
		def interpret(self, frame):
			raise _FakeKvdNoMessage()

	can = _make_can()
	can._dbc = _RaisingDbc()

	assert can.decode(SimpleNamespace()) is None


def test_decode_uses_value_not_phys_so_an_enum_signal_shows_its_label():
	"""Regression test.

	kvadblib's BoundSignal.phys is always the raw physical number, even for
	an enum (value-table) signal - decode() used to return that directly,
	so e.g. a lamp/fan status signal showed as a bare "1.0" everywhere it
	was decoded (CAN Viewer tree, TX Settings) instead of its DBC-defined
	label like "On". BoundSignal.value returns the matching label for an
	enum signal and falls back to .phys for every other signal, so decode()
	now reads that instead.
	"""
	enum_signal = _FakeInterpretSignal(name="FanStatus", value="On", phys=1.0)
	plain_signal = _FakeInterpretSignal(name="CoolantTemp", value=-20.0, phys=-20.0)

	class _FakeDbcInterpret:
		def interpret(self, frame):
			return [enum_signal, plain_signal]

	can = _make_can()
	can._dbc = _FakeDbcInterpret()

	result = can.decode(SimpleNamespace())

	assert result == {"FanStatus": "On", "CoolantTemp": -20.0}


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


def _fake_ext_canlib_can(ext_flag=0x4):
	class _FakeCanNoMsg(Exception):
		pass

	return SimpleNamespace(MessageFlag=SimpleNamespace(EXT=ext_flag), CanNoMsg=_FakeCanNoMsg)


def test_feed_dm1_ignores_standard_id_frames(monkeypatch):
	"""J1939 always uses 29-bit extended ids, so a standard-id frame can't be J1939 traffic."""
	monkeypatch.setattr(can_module, "_canlib_can", lambda: _fake_ext_canlib_can(ext_flag=0x4))

	can = _make_can()
	can._dm1_decoder = can_module.Dm1TransportDecoder()
	standard_frame = SimpleNamespace(id=0x123, data=b"\x00\x00", flags=0)

	assert can.feed_dm1(standard_frame) is None


def test_feed_dm1_decodes_an_extended_id_dm1_frame(monkeypatch):
	ext_flag = 0x4
	monkeypatch.setattr(can_module, "_canlib_can", lambda: _fake_ext_canlib_can(ext_flag=ext_flag))

	can = _make_can()
	can._dm1_decoder = can_module.Dm1TransportDecoder()
	dm1_can_id = 0x18FECA17  # PGN 0xFECA (DM1), source address 0x17
	dm1_frame = SimpleNamespace(id=dm1_can_id, data=bytearray([0x00, 0x00]), flags=ext_flag)

	result = can.feed_dm1(dm1_frame)

	assert result is not None
	assert result.source_address == 0x17


def test_feed_dm2_ignores_standard_id_frames(monkeypatch):
	"""J1939 always uses 29-bit extended ids, so a standard-id frame can't be J1939 traffic."""
	monkeypatch.setattr(can_module, "_canlib_can", lambda: _fake_ext_canlib_can(ext_flag=0x4))

	can = _make_can()
	can._dm2_decoder = can_module.Dm2TransportDecoder()
	standard_frame = SimpleNamespace(id=0x123, data=b"\x00\x00", flags=0)

	assert can.feed_dm2(standard_frame) is None


def test_feed_dm2_decodes_an_extended_id_dm2_frame(monkeypatch):
	ext_flag = 0x4
	monkeypatch.setattr(can_module, "_canlib_can", lambda: _fake_ext_canlib_can(ext_flag=ext_flag))

	can = _make_can()
	can._dm2_decoder = can_module.Dm2TransportDecoder()
	dm2_can_id = 0x18FECB17  # PGN 0xFECB (DM2), source address 0x17
	dm2_frame = SimpleNamespace(id=dm2_can_id, data=bytearray([0x00, 0x00]), flags=ext_flag)

	result = can.feed_dm2(dm2_frame)

	assert result is not None
	assert result.source_address == 0x17
