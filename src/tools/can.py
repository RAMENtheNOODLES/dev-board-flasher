from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Iterator, Optional, Union, Generator, Any

import canlib

if TYPE_CHECKING:
	import canlib.canlib as canlib_can
	import canlib.kvadblib as kvadblib
	from canlib.kvadblib.message import Message

DecodedFrame = dict[str, object]


def _canlib_can():
	"""Lazily import canlib.canlib.

	This submodule loads the Kvaser CANlib DLL as soon as it is imported, which
	fails on machines without Kvaser drivers installed. Importing it lazily
	means the rest of the app works fine on machines without CAN hardware, and
	the DLL failure only happens when CAN features are actually used.
	"""
	import canlib.canlib as canlib_can

	return canlib_can


def _kvadblib():
	"""Lazily import canlib.kvadblib, see `_canlib_can` for why."""
	import canlib.kvadblib as kvadblib

	return kvadblib


class CAN:
	"""Wraps a Kvaser CANlib channel on a specific device, optionally decoding
	traffic with a DBC file."""

	def __init__(
		self,
		device: canlib.Device,
		channel: int = 0,
		dbc_path: Optional[Union[str, Path]] = None,
		bitrate: Optional["canlib_can.Bitrate"] = None,
	) -> None:
		"""Configures a channel on ``device``, optionally loading a DBC file.

		The channel itself is not opened yet; call :meth:`open` (or use this
		as a context manager) before sending/receiving.

		Args:
			device (canlib.Device): The CAN device to use.
			channel (int, optional): Local channel number on ``device``.
				Defaults to ``0``.
			dbc_path (str | Path | None, optional): Path to a DBC file to load
				immediately via :meth:`load_dbc`. Defaults to ``None`` (no
				decoding available until :meth:`load_dbc` is called).
			bitrate (canlib_can.Bitrate | None, optional): Bus bitrate to use
				when the channel is opened. Defaults to ``BITRATE_500K``.
		"""
		self.logger = logging.getLogger(__name__)
		self.device = device
		self.channel = channel
		self.bitrate = bitrate if bitrate is not None else _canlib_can().Bitrate.BITRATE_500K

		self._channel: Optional["canlib_can.Channel"] = None
		self._dbc: Optional["kvadblib.Dbc"] = None
		# Set once receive() has warned about bus error frames, so it only
		# logs the first one per connection instead of once per error.
		self._warned_about_errors = False

		if dbc_path is not None:
			self.load_dbc(dbc_path)

	@staticmethod
	def poke_can_bus() -> bool:
		"""Logs the first connected CAN device's info, if any.

		Returns:
			bool: ``True`` if at least one CAN device is connected, ``False``
				otherwise.
		"""
		logger = logging.getLogger(__name__)
		for dev in canlib.connected_devices():
			logger.debug(dev.probe_info())
			return True
		else:
			return False

	@staticmethod
	def list_devices() -> list[canlib.Device]:
		"""Return every currently connected CAN device."""
		_canlib_can().enumerate_hardware()
		return list(canlib.connected_devices())

	@staticmethod
	def list_devices_with_channels() -> list[tuple[str, int, list[int]]]:
		"""Return every currently connected CAN device as its product name,
		serial number, and the local channel numbers available on it."""
		canlib_can = _canlib_can()
		canlib_can.enumerate_hardware()

		devices: list[tuple[str, int, list[int]]] = []
		device_index: dict[tuple, int] = {}

		channel_number = 0
		while True:
			try:
				data = canlib_can.ChannelData(channel_number)
				ean = data.card_upc_no
				serial = data.card_serial_no
				name = data.devdescr_ascii
				chan_no_on_card = data.chan_no_on_card
			except canlib_can.CanNotFound:
				break
			except canlib_can.exceptions.CanError as e:
				if e.canERRstatus == canlib_can.enums.Error.NOCARD: # pyright: ignore[reportAttributeAccessIssue]
					channel_number += 1
					continue
				raise

			key = (ean, serial)
			if key not in device_index:
				device_index[key] = len(devices)
				devices.append((name, serial, [])) # pyright: ignore[reportArgumentType]
			devices[device_index[key]][2].append(chan_no_on_card) # pyright: ignore[reportArgumentType]

			channel_number += 1

		return devices

	@staticmethod
	def check_for_libraries() -> bool:
		try:
			_canlib_can()

			return True
		except FileNotFoundError:
			return False

	@property
	def is_open(self) -> bool:
		"""bool: Whether the channel is currently open (via :meth:`open`)."""
		return self._channel is not None

	@property
	def has_dbc(self) -> bool:
		"""bool: Whether a DBC file is currently loaded (via :meth:`load_dbc`)."""
		return self._dbc is not None

	@property
	def get_dbc_messages(self) -> Generator[Message, Any, None]|None:
		"""Generator[Message, Any, None] | None: The loaded DBC's messages, or ``None`` if no DBC is loaded."""
		if self._dbc is not None:
			return self._dbc.messages()
		else:
			return None

	def dbc_message_signals(self) -> dict[int, tuple[str, list[tuple[str, str]]]]:
		"""Return ``{message_id: (message_name, [(signal_name, unit), ...])}`` for the loaded DBC file.

		Keyed by numeric message ID since that's what incoming frames are
		matched against, but the message name is carried alongside it since
		that's what should actually be shown to the user. Each signal's unit
		(``""`` if the DBC doesn't define one) is included alongside its name
		since it's static per-signal metadata, unlike its decoded value which
		only exists once a matching frame has actually been received.

		Walking every message/signal via kvadblib is comparatively slow for a
		DBC of any real size, so callers driving a GUI should run this off
		the main thread (see ``CanWorker``) rather than call it directly from
		a UI event handler.
		"""
		if self._dbc is None:
			return {}

		# Message.id sets bit 31 (kvadblib.MessageFlag.EXT) as an extended-id
		# marker, but a received Frame's raw .id never has that bit set (its
		# extended-ness lives in .flags instead), so it has to be stripped
		# here to match what frames are actually keyed by.
		ext_flag = _kvadblib().MessageFlag.EXT
		return {
			msg.id & ~ext_flag: (msg.name, [(signal.name, signal.unit) for signal in msg.signals()])
			for msg in self._dbc.messages()
		}

	def load_dbc(self, dbc_path: Optional[Union[str, Path]]) -> None:
		"""Load a DBC file, used to decode/encode messages by name.

		Pass `None` to clear any currently loaded DBC, e.g. when the caller
		wants to stop decoding without having a replacement file to load.
		"""
		if self._dbc is not None:
			self._dbc.close()
			self._dbc = None

		if dbc_path is None:
			return

		dbc_path = Path(dbc_path)
		if not dbc_path.is_file():
			self.logger.warning(f"DBC file not found: {dbc_path}")
			return

		self.logger.debug("Loading DBC file %s", dbc_path)
		self._dbc = _kvadblib().Dbc(filename=str(dbc_path))

	def set_device(self, device: canlib.Device) -> None:
		"""Change the target device, reopening the channel if it is currently open."""
		reopen = self.is_open
		if reopen:
			self.close()
		self.device = device
		if reopen:
			self.open()

	def set_channel(self, channel: int) -> None:
		"""Change the channel number, reopening the channel if it is currently open."""
		reopen = self.is_open
		if reopen:
			self.close()
		self.channel = channel
		if reopen:
			self.open()

	def set_bitrate(self, bitrate: "canlib_can.Bitrate") -> None:
		"""Change the bitrate, reopening the channel if it is currently open."""
		reopen = self.is_open
		if reopen:
			self.close()
		self.bitrate = bitrate
		if reopen:
			self.open()

	def open(self) -> None:
		"""Open the configured channel on the device and go bus on."""
		if self._channel is not None:
			return

		canlib_can = _canlib_can()
		self.logger.debug(
			"Opening channel %s on device %s", self.channel, self.device
		)
		channel = self.device.open_channel(
			chan_no_on_card=self.channel, flags=canlib_can.Open.ACCEPT_VIRTUAL
		)
		channel.setBusParams(self.bitrate)
		channel.busOn()
		self._channel = channel
		self._warned_about_errors = False

	def close(self) -> None:
		"""Go bus off and close the channel, if open."""
		if self._channel is None:
			return

		self.logger.debug("Closing channel %s on device %s", self.channel, self.device)
		self._channel.busOff()
		self._channel.close()
		self._channel = None

	def __enter__(self) -> "CAN":
		self.open()
		return self

	def __exit__(self, exc_type, exc_val, exc_tb) -> None:
		self.close()

	def send(self, frame_id: int, data: bytes, extended: bool = False) -> None:
		"""Send a raw CAN frame."""
		if self._channel is None:
			raise RuntimeError("CAN channel is not open")

		canlib_can = _canlib_can()
		flags = canlib_can.MessageFlag.EXT if extended else canlib_can.MessageFlag.STD
		frame = canlib.Frame(id_=frame_id, data=data, flags=flags)
		self._channel.write(frame)

	def send_message(self, name: str, **signal_values: float) -> None:
		"""Encode and send a message by name using the loaded DBC file."""
		if self._channel is None:
			raise RuntimeError("CAN channel is not open")
		if self._dbc is None:
			raise RuntimeError("No DBC file loaded")

		message = self._dbc.get_message_by_name(name)
		frame = message.asframe()
		bound_message = message.bind(frame)
		for signal_name, value in signal_values.items():
			getattr(bound_message, signal_name).phys = value

		self._channel.write(frame)

	def receive(self, timeout: int = 500) -> Optional["canlib.Frame"]:
		"""Read a single raw frame, or `None` on timeout.

		Always returns the raw `canlib.Frame` (id/dlc/data/timestamp intact)
		regardless of whether a DBC is loaded, since callers that need the
		frame's own fields (e.g. building a live message list) shouldn't lose
		them just because its signals happen to be decodable. Use `decode` to
		additionally get its signal values.
		"""
		if self._channel is None:
			raise RuntimeError("CAN channel is not open")

		canlib_can = _canlib_can()
		try:
			frame = self._channel.read(timeout=timeout)
		except canlib_can.CanNoMsg:
			return None

		if frame.flags & canlib_can.MessageFlag.ERROR_FRAME:
			# The driver synthesizes these instead of a real frame when the
			# channel can't successfully read anything off the wire - most
			# often a bitrate mismatch with the actual bus. Treat like a
			# timeout rather than surfacing it as bus traffic.
			if not self._warned_about_errors:
				self._warned_about_errors = True
				self.logger.warning(
					"Receiving CAN bus error frames instead of real traffic - "
					"the channel's bitrate (%s) likely doesn't match the bus.",
					self.bitrate,
				)
			return None

		return frame

	def decode(self, frame: "canlib.Frame") -> Optional[DecodedFrame]:
		"""Decode `frame`'s signals using the loaded DBC file.

		Returns `None` if no DBC is loaded or the frame's message isn't in it.
		"""
		if self._dbc is None:
			return None

		try:
			bound_message = self._dbc.interpret(frame)
		except _kvadblib().KvdNoMessage:
			return None

		return {signal.name: signal.phys for signal in bound_message}

	def __iter__(self) -> Iterator["canlib.Frame"]:
		"""Yield frames as they arrive until the channel is closed."""
		while self.is_open:
			frame = self.receive()
			if frame is not None:
				yield frame
