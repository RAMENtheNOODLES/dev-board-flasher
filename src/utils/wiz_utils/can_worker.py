from threading import Event

from PySide6.QtCore import Signal, QObject, Slot

from .plain_runnable import PlainRunnable
from tools.can import CAN


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
	# Emitted for each frame/decoded message read off the bus
	frame_received = Signal(object)
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

	def __init__(self, task_id: str, stop_event: Event, can_instance: CAN, receive_timeout: int = 100):
		super().__init__(task_id, stop_event)
		self.signals = CanWorkerSignals()
		self.can = can_instance
		self.receive_timeout = receive_timeout

	@Slot()
	def run(self):
		try:
			dbc_data = self.can.dbc_message_signals()
		except Exception as e:
			self.signals.error.emit(str(e))
			return

		self.signals.dbc_ready.emit(dbc_data)

		try:
			self.can.open()
		except Exception as e:
			self.signals.error.emit(str(e))
			return

		self.signals.connected.emit()

		try:
			while not self.stop_event.is_set() and self.can.is_open:
				msg = self.can.receive(self.receive_timeout)
				if msg is not None:
					self.signals.frame_received.emit(msg)
		except Exception as e:
			self.signals.error.emit(str(e))
		finally:
			self.can.close()
			self.signals.disconnected.emit()
