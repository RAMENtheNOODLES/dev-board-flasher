import queue
from threading import Event
from time import monotonic

from PySide6.QtCore import QObject, Signal, Slot

from tools.can import CAN

from .plain_runnable import PlainRunnable


class CanWorkerSignals(QObject):
	# Emitted once the loaded DBC's messages/signals have been walked, as
	# {message_id: [signal names]}. Signal(object), not Signal(dict): this
	# crosses threads via a queued connection, and Qt's dict marshaling for
	# queued connections requires string keys (QVariantMap), which fails
	# silently (a Shiboken conversion warning) for the int message ID keys
	# used here.
	dbc_ready = Signal(object)
	# Emitted once the channel has been opened and gone bus on
	connected = Signal()
	# Emitted after the channel has been closed, whether that was requested
	# via stop_event or forced by an error
	disconnected = Signal()
	# Emitted for each raw frame read off the bus
	frame_received = Signal(object)
	# Emitted for each frame this app successfully transmits (see enqueue_send/_flush_send_queue)
	frame_sent = Signal(object)
	# Emitted periodically (see CanWorker._BUS_LOAD_POLL_INTERVAL) with the
	# current CAN bus load as a percentage (0.0-100.0)
	bus_load_updated = Signal(float)
	# Emitted with a message if opening or reading the channel raises
	error = Signal(str)


class CanWorker(PlainRunnable):
	"""Owns a `CAN` channel's open/receive/close lifecycle on a background thread.

	`CAN.open()` and `CAN.receive()` are blocking calls into the Kvaser
	CANlib driver, so running them straight from the GUI thread (as
	`CANViewer.connect_can` and its receive-loop `QTimer` used to) freezes
	the app for however long the driver takes to respond. This runs that
	same sequence on a `QThreadPool` thread instead, reporting back to the
	GUI via signals. Once started, `can_instance`'s channel must only be
	touched from here until `disconnected` fires, since `CANViewer` also
	closes/reopens it (e.g. on device/channel/bitrate changes) and doing so
	from both threads at once would race on the same CANlib handle.
	"""

	# How often, in seconds, `run()` polls `CAN.bus_load()` while connected.
	_BUS_LOAD_POLL_INTERVAL: float = 1.0

	def __init__(self, task_id: str, stop_event: Event, can_instance: CAN, receive_timeout: int = 100):
		"""Prepares the worker to drive ``can_instance``'s connect/receive loop.

		Args:
			task_id (str): Identifier for this task (see :class:`PlainRunnable`).
			stop_event (Event): Set by the caller to request a graceful stop.
			can_instance (CAN): The CAN channel to open and read from. Must
				not be touched from another thread once :meth:`run` starts,
				until ``disconnected`` fires.
			receive_timeout (int, optional): Timeout, in milliseconds, passed
				to each ``CAN.receive`` call. Defaults to ``100``.
		"""
		super().__init__(task_id, stop_event)
		self.signals = CanWorkerSignals()
		self.can = can_instance
		self.receive_timeout = receive_timeout
		# Thread-safe: enqueue_send() is called from the GUI thread (see
		# TxScheduler), but the actual CAN.send_message() call is only ever
		# made from run()'s own loop below, since the channel must not be
		# touched from more than one thread at once.
		self._send_queue: queue.Queue[tuple[str, dict[str, float]]] = queue.Queue()

	def enqueue_send(self, message_name: str, signal_values: dict[str, float]) -> None:
		"""Queues a DBC message to be sent by `run`'s loop, on this worker's own thread."""
		self._send_queue.put((message_name, signal_values))

	def _flush_send_queue(self) -> None:
		"""Sends every currently-queued message. Only ever called from `run`'s own thread."""
		while True:
			try:
				message_name, signal_values = self._send_queue.get_nowait()
			except queue.Empty:
				return

			try:
				frame = self.can.send_message(message_name, **signal_values)
			except Exception as e:  # noqa: BLE001 - a bad TX config shouldn't kill the receive loop
				self.signals.error.emit(str(e))
			else:
				self.signals.frame_sent.emit(frame)

	@Slot()
	def run(self):
		"""Walks the DBC (if any), opens the channel, and receives frames until stopped.

		Emits ``dbc_ready`` with the DBC's messages/signals first (even if
		none are loaded), then ``connected`` once the channel is open, then
		``frame_received`` for each frame read off the bus. Each loop
		iteration also flushes any messages queued via :meth:`enqueue_send`
		first, emitting ``frame_sent`` for each one actually transmitted, so
		periodic TX sends (see ``TxScheduler``) go out from this same thread
		rather than racing the channel from the GUI thread. Also emits
		``bus_load_updated`` roughly every :data:`_BUS_LOAD_POLL_INTERVAL`
		seconds) until ``stop_event`` is set or the channel closes, then
		``disconnected``. Any exception along the way is reported via
		``error`` instead of propagating, and the channel is always closed
		before returning.
		"""
		try:
			dbc_data = self.can.dbc_message_signals()
		except Exception as e:  # noqa: BLE001 - intentionally broad, see run()'s docstring
			self.signals.error.emit(str(e))
			return

		self.signals.dbc_ready.emit(dbc_data)

		try:
			self.can.open()
		except Exception as e:  # noqa: BLE001 - intentionally broad, see run()'s docstring
			self.signals.error.emit(str(e))
			return

		self.signals.connected.emit()

		# Starts the clock from here rather than 0.0, so the first poll is a
		# full _BUS_LOAD_POLL_INTERVAL after connecting rather than immediate.
		last_bus_load_poll = monotonic()
		try:
			while not self.stop_event.is_set() and self.can.is_open:
				self._flush_send_queue()

				msg = self.can.receive(self.receive_timeout)
				if msg is not None:
					self.signals.frame_received.emit(msg)

				now = monotonic()
				if now - last_bus_load_poll >= self._BUS_LOAD_POLL_INTERVAL:
					last_bus_load_poll = now
					self.signals.bus_load_updated.emit(self.can.bus_load())
		except Exception as e:  # noqa: BLE001 - intentionally broad, see run()'s docstring
			self.signals.error.emit(str(e))
		finally:
			self.can.close()
			self.signals.disconnected.emit()
