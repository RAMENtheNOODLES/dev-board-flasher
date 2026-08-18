from threading import Event

from PySide6.QtCore import QObject, Signal, Slot

# Example using cross-platform 'usb-monitor' package (pip install usb-monitor)
from usbmonitor import USBMonitor

from .plain_runnable import PlainRunnable


class USBWorkerSignals(QObject):
	"""Signals emitted by :class:`USBWorker` as USB devices connect/disconnect."""

	# Custom signal carrying device info dictionary
	device_connected = Signal(dict)
	device_disconnected = Signal(dict)


class USBWorker(PlainRunnable):
	"""Watches for USB device connect/disconnect events on a background thread.

	Wraps the `usb-monitor` package's polling monitor, which spawns its own
	background thread, so :meth:`run` mainly exists to keep that thread's
	lifetime tied to ``stop_event`` and to re-emit its callbacks as Qt
	signals for the GUI thread (e.g. to refresh the serial port list).
	"""

	def __init__(self, task_id: str, stop_event: Event):
		"""Prepares the worker; the underlying USB monitor isn't started until :meth:`run`.

		Args:
			task_id (str): Identifier for this task (see :class:`PlainRunnable`).
			stop_event (Event): Set by the caller to stop monitoring.
		"""
		super().__init__(task_id, stop_event)
		self.signals = USBWorkerSignals()

	@Slot()
	def run(self):
		"""Starts USB monitoring and blocks until ``stop_event`` is set.

		Each connect/disconnect reported by the underlying monitor is
		re-emitted as ``device_connected``/``device_disconnected``. Stops the
		monitor's own background thread before returning.
		"""
		monitor = USBMonitor()
		# Callback triggered on connect
		def on_connect(device_id, device_info):
			self.signals.device_connected.emit(device_info)

		def on_disconnect(device_id, device_info):
			self.signals.device_disconnected.emit(device_info)

		monitor.start_monitoring(on_connect=on_connect, on_disconnect=on_disconnect)

		# start_monitoring() spawns its own background polling thread and
		# returns immediately, so this run() would otherwise exit right away
		# and leave that thread with nothing tracking its lifetime. Block
		# here until the caller signals shutdown via stop_event, then stop
		# the monitor's thread before this QRunnable finishes.
		self.stop_event.wait()
		monitor.stop_monitoring()