from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Iterator, Optional, Union

import canlib

if TYPE_CHECKING:
	import canlib.canlib as canlib_can
	import canlib.kvadblib as kvadblib

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
		self.logger = logging.getLogger(__name__)
		self.device = device
		self.channel = channel
		self.bitrate = bitrate if bitrate is not None else _canlib_can().Bitrate.BITRATE_500K

		self._channel: Optional["canlib_can.Channel"] = None
		self._dbc: Optional["kvadblib.Dbc"] = None

		if dbc_path is not None:
			self.load_dbc(dbc_path)

	@staticmethod
	def poke_can_bus() -> bool:
		logger = logging.getLogger(__name__)
		for dev in canlib.connected_devices():
			logger.debug(dev.probe_info())
			return True
		else:
			return False

	@staticmethod
	def list_devices() -> list[canlib.Device]:
		"""Return every currently connected CAN device."""
		return list(canlib.connected_devices())

	@staticmethod
	def list_devices_with_channels() -> list[tuple[str, int, list[int]]]:
		"""Return every currently connected CAN device as its product name,
		serial number, and the local channel numbers available on it."""
		canlib_can = _canlib_can()

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
				if e.canERRstatus == canlib_can.enums.Error.NOCARD:
					channel_number += 1
					continue
				raise

			key = (ean, serial)
			if key not in device_index:
				device_index[key] = len(devices)
				devices.append((name, serial, []))
			devices[device_index[key]][2].append(chan_no_on_card)

			channel_number += 1

		return devices

	@property
	def is_open(self) -> bool:
		return self._channel is not None

	@property
	def has_dbc(self) -> bool:
		return self._dbc is not None

	def load_dbc(self, dbc_path: Union[str, Path]) -> None:
		"""Load a DBC file, used to decode/encode messages by name."""
		dbc_path = Path(dbc_path)
		if not dbc_path.is_file():
			raise FileNotFoundError(f"DBC file not found: {dbc_path}")

		self.logger.debug("Loading DBC file %s", dbc_path)
		if self._dbc is not None:
			self._dbc.close()
		self._dbc = _kvadblib().Dbc(filename=str(dbc_path))

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

	def receive(self, timeout: int = 500) -> Optional[Union["canlib.Frame", DecodedFrame]]:
		"""Read a single frame.

		Returns the decoded signals as a dict if a DBC is loaded and the frame's
		message is known, the raw `canlib.Frame` if not, or `None` on timeout.
		"""
		if self._channel is None:
			raise RuntimeError("CAN channel is not open")

		try:
			frame = self._channel.read(timeout=timeout)
		except _canlib_can().CanNoMsg:
			return None

		if self._dbc is None:
			return frame

		try:
			bound_message = self._dbc.interpret(frame)
		except _kvadblib().KvdNoMessage:
			self.logger.debug("No DBC message found for frame id 0x%X", frame.id)
			return frame

		return {signal.name: signal.phys for signal in bound_message}

	def __iter__(self) -> Iterator[Union["canlib.Frame", DecodedFrame]]:
		"""Yield frames as they arrive until the channel is closed."""
		while self.is_open:
			frame = self.receive()
			if frame is not None:
				yield frame
