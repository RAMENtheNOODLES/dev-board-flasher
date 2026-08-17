from threading import Event

from PySide6.QtCore import Signal, QObject, Slot

# Example using cross-platform 'usb-monitor' package (pip install usb-monitor)
from usbmonitor import USBMonitor
from .plain_runnable import PlainRunnable

class USBWorkerSignals(QObject):
	# Custom signal carrying device info dictionary
	device_connected = Signal(dict)
	device_disconnected = Signal(dict)


class USBWorker(PlainRunnable):
	def __init__(self, task_id: str, stop_event: Event):
		super().__init__(task_id, stop_event)
		self.signals = USBWorkerSignals()

	@Slot()
	def run(self):
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