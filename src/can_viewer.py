import csv
import logging
import threading
from datetime import datetime
from typing import TextIO

from canlib import Device
from canlib.frame import Frame
from PySide6.QtCore import QCoreApplication, QThreadPool, QTimer
from PySide6.QtGui import QFont, QFontDatabase, QIcon
from PySide6.QtWidgets import QFileDialog, QMainWindow, QMessageBox

from tools.can import CAN
from ui_can import Ui_CANViewer
from utils.wiz_utils.can_worker import CanWorker
from utils.wiz_utils.stored_settings import StoredSettings


def _bitrate_enum():
	"""Lazily import canlib.canlib.enums.Bitrate.

	Mirrors tools.can._canlib_can(): importing canlib.canlib eagerly loads
	the Kvaser CANlib DLL immediately, which would otherwise crash the
	whole app at import time (before __init__'s own "CANLib drivers not
	installed" handling ever gets a chance to run) on a machine that
	doesn't have it installed.
	"""
	from canlib.canlib.enums import Bitrate

	return Bitrate


class CANViewer(QMainWindow, Ui_CANViewer):
	"""Standalone window for connecting to a Kvaser CAN device and viewing/decoding traffic.

	Opened via **Tools > CAN** (see :meth:`main.MainWindow.open_can_viewer`),
	which reuses a single instance across shows rather than recreating it.
	Device/channel selection and bus connect/disconnect run on a dedicated
	:class:`~PySide6.QtCore.QThreadPool` through :class:`CanWorker`, so the
	blocking CANlib calls don't freeze this window's UI thread.
	"""

	_CAN_SAMPLE_RATE: int = 100

	def __init__(self, parent = None) -> None:
		"""Builds the window, loads the bundled font, and populates devices/channels.

		If the Kvaser CANlib drivers aren't installed, shows a warning dialog
		and closes the window instead of finishing initialization.

		Args:
			parent (QWidget, optional): Parent widget for the window.
				Defaults to ``None``.
		"""
		super().__init__(parent)

		self.dev: Device|None = None
		self.logger = logging.getLogger(__name__)

		self.setupUi(self)
		# Set icon
		self.setWindowIcon(QIcon(":/logo.png"))
		font_id = QFontDatabase.addApplicationFont(":/FiraCodeNerdFont-Regular.ttf")
		
		if font_id != -1:
			# 4. Extract the exact internal font family name
			font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
		
			# 5. Create a font object and apply it globally to the app
			global_font = QFont(font_family, 12)  # Family name and default size
			self.setFont(global_font)
			self.logger.info("Done Initializing Fonts")
		else:
			self.logger.error("Error: Could not load font from resources.")
		
		QCoreApplication.setOrganizationDomain("CookieJAR")
		QCoreApplication.setApplicationName("flashwiz")

		# init CAN
		try:
			Bitrate = _bitrate_enum()
			self._BIT_RATES = [Bitrate.BITRATE_125K, Bitrate.BITRATE_250K, Bitrate.BITRATE_500K, Bitrate.BITRATE_1M]
			self.populate_devices()
			self.populate_channels()
		except FileNotFoundError:
			self.logger.warning("CANLib drivers not installed. Visit https://kvaser.com/canlib-sdk/ to install them...")

			QMessageBox.critical(
				self,
				"CANLib drivers not installed",
				"CANLib drivers are not installed, please visit https://kvaser.com/canlib-sdk/ to install them before using this tool.",
				QMessageBox.StandardButton.Ok
			)

			self.close()
			# Without this, the rest of __init__ still runs against a window
			# that's already being closed and never finished initializing
			# (self._BIT_RATES/self.dev never got set), crashing anyway.
			return

		# configure function connections
		self.can = None
		# Dedicated pool, not QThreadPool.globalInstance(): closeEvent()
		# blocks on waitForDone(), and the global pool also runs the main
		# window's long-lived USB_Monitor worker, which would make closing
		# this window hang until the whole app exits.
		self.thread_pool = QThreadPool(self)
		self.worker: CanWorker | None = None
		self.stop_event: threading.Event | None = None

		self.log_file: TextIO | None = None
		self.log_writer = None
		self.actionSto_p_Logging.setEnabled(False)

		self.device_check_timer = QTimer(self)
		self.device_check_timer.timeout.connect(self.populate_devices)
		self.action_Load_DBC.triggered.connect(self.load_dbc)
		self.action_Start_Logging.triggered.connect(self.start_logging)
		self.actionSto_p_Logging.triggered.connect(self.stop_logging)
		self.useDBCCheckBox.toggled.connect(self._sync_dbc)
		self.deviceSelect.currentIndexChanged.connect(self.populate_channels)
		self.deviceSelect.currentIndexChanged.connect(self.selected_device)
		self.connectButton.clicked.connect(self.connect_can)
		self.channelSelect.currentIndexChanged.connect(self.selected_channel)
		self.baudRateComboBox.currentIndexChanged.connect(self.selected_baudrate)

		self.dbc_file = StoredSettings.CAN_DBC_FILE.get(None)

		self.selected_device(0)
		self.selected_channel(0)

	def populate_devices(self):
		"""Repopulates the device dropdown with currently connected CAN devices.

		Connected to the main window's USB monitor signals, so the list stays
		current as devices are plugged/unplugged, in addition to the initial
		call from :meth:`__init__`.
		"""
		self.deviceSelect.clear()
		for dev, serial, channels in CAN.list_devices_with_channels():
			self.deviceSelect.addItem(f"{dev} : {serial}", channels)

	def populate_channels(self):
		"""Repopulates the channel dropdown with the currently selected device's channels."""
		self.channelSelect.clear()
		channels = self.deviceSelect.currentData()
		if channels is not None:
			for channel in channels:
				self.channelSelect.addItem(f"Channel: {channel}")

	def selected_device(self, index):
		"""Applies a newly selected device from the device dropdown to ``self.can``.

		Args:
			index (int): Index of the selected device, matching
				:meth:`CAN.list_devices`.
		"""
		self.dev = CAN.list_devices()[index]
		if self.can is None and self.dev is not None:
			self.can = CAN(self.dev, 0, self._dbc_file_if_enabled(), self._BIT_RATES[self.baudRateComboBox.currentIndex()])
		else:
			# These should not be none due to the if statement above
			assert self.can is not None
			assert self.dev is not None

			self.can.set_channel(0)
			self.can.set_device(self.dev)
			self.can.set_bitrate(self._BIT_RATES[self.baudRateComboBox.currentIndex()])

		self._update_device_info()

	def _update_device_info(self) -> None:
		"""Refreshes the read-only info box with the selected device's `probe_info()`.

		Falls back to the box's placeholder text ("No device found") when
		nothing is selected.
		"""
		self.deviceInfo.setPlainText(self.dev.probe_info() if self.dev is not None else "")

	def selected_channel(self, index):
		"""Applies a newly selected channel from the channel dropdown to ``self.can``.

		Args:
			index (int): The selected local channel number.
		"""
		self.channel = index
		if self.can is not None:
			self.can.set_channel(index)

	def selected_baudrate(self, index):
		"""Applies a newly selected bitrate from the baud rate dropdown to ``self.can``.

		Args:
			index (int): Index into ``self._BIT_RATES`` of the selected bitrate.
		"""
		if self.can is not None:
			self.can.set_bitrate(self._BIT_RATES[index])

	def load_dbc(self):
		"""Opens a file picker for choosing a DBC file and applies it to ``self.can``.

		The chosen path is persisted to :data:`StoredSettings.CAN_DBC_FILE`.
		No-op if the dialog is cancelled.
		"""
		dbc_file, _ = QFileDialog.getOpenFileName(
			self,
			"Open File",
			StoredSettings.CAN_DBC_FILE.get(""),
			"CAN Database Files (*.dbc)"
		)

		if not dbc_file:
			return

		self.dbc_file = dbc_file
		StoredSettings.CAN_DBC_FILE.set(self.dbc_file)

		# Walking the loaded DBC's messages/signals is slow enough that it
		# belongs off the GUI thread (see CanWorker.run), so the tree itself
		# only refreshes on the next connect rather than here.
		self._sync_dbc()

	def _dbc_file_if_enabled(self) -> str | None:
		"""Returns the loaded DBC path, or `None` if "Use DBC File" is unchecked."""
		return self.dbc_file if self.useDBCCheckBox.isChecked() else None

	def _sync_dbc(self) -> None:
		"""Applies the current DBC path (or lack of one) to `self.can`.

		Called whenever a new DBC file is loaded or the "Use DBC File"
		checkbox is toggled, so decoding (`CAN.decode`) reflects the current
		choice immediately. The tree's known-message list only comes from
		`CanWorker.run`'s startup walk though, so it still only picks up the
		change on the next connect.
		"""
		if self.can is not None:
			self.can.load_dbc(self._dbc_file_if_enabled())

	def connect_can(self):
		"""Toggles the CAN connection: starts a :class:`CanWorker`, or asks the running one to stop.

		If already connected/connecting, requests a graceful stop via
		``self.stop_event`` rather than touching the worker directly from
		this thread. Otherwise starts a new :class:`CanWorker` on
		``self.thread_pool`` and wires its signals to this window's handlers.
		"""
		if self.worker is not None and self.stop_event is not None:
			# Already connected/connecting: ask the worker to close the
			# channel and stop, rather than touching it from this thread.
			self.connectButton.setEnabled(False)
			self.connectButton.setText("Disconnecting...")
			self.stop_event.set()
			return

		if self.can is None and self.dev is not None:
			self.can = CAN(self.dev, self.channel, self._dbc_file_if_enabled(), self._BIT_RATES[self.baudRateComboBox.currentIndex()])

		# This should never be none due to the if statement above
		assert self.can is not None

		self.logger.debug(f"CAN Baudrate: {self._BIT_RATES[self.baudRateComboBox.currentIndex()]}")

		self.connectButton.setEnabled(False)
		self.connectButton.setText("Connecting...")
		self._set_controls_enabled(False)

		stop_event = threading.Event()
		worker = CanWorker("CAN_Connection", stop_event, self.can, self._CAN_SAMPLE_RATE // 2)
		worker.signals.dbc_ready.connect(self.canLogs.populate_tree)
		worker.signals.connected.connect(self._on_can_connected)
		worker.signals.disconnected.connect(self._on_can_disconnected)
		worker.signals.frame_received.connect(self._on_frame_received)
		worker.signals.error.connect(self._on_can_error)

		self.stop_event = stop_event
		self.worker = worker
		self.thread_pool.start(worker)

	def _set_controls_enabled(self, enabled: bool) -> None:
		"""Enables/disables the device/channel/baud rate controls and Load DBC action.

		Called while a connection is in progress or open, so the device
		being used can't be changed out from under the running
		:class:`CanWorker`.

		Args:
			enabled (bool): Whether the controls should be enabled.
		"""
		self.deviceSelect.setEnabled(enabled)
		self.channelSelect.setEnabled(enabled)
		self.baudRateComboBox.setEnabled(enabled)
		self.action_Load_DBC.setEnabled(enabled)

	def _on_can_connected(self):
		"""Updates the connect button once the worker's channel is open. Connected to ``CanWorker.signals.connected``."""
		self.connectButton.setEnabled(True)
		self.connectButton.setText("Disconnect")

	def _on_can_disconnected(self):
		"""Clears the worker/stop event and restores controls once the channel is closed. Connected to ``CanWorker.signals.disconnected``."""
		self.worker = None
		self.stop_event = None
		self.connectButton.setEnabled(True)
		self.connectButton.setText("Connect")
		self._set_controls_enabled(True)

	def _on_can_error(self, message: str):
		"""Logs and shows a worker error. Connected to ``CanWorker.signals.error``.

		Args:
			message (str): Description of the error raised on the worker
				thread.
		"""
		self.logger.error(f"CAN error: {message}")
		QMessageBox.critical(self, "CAN Error", message)

	def _on_frame_received(self, frame: Frame):
		"""Updates the message tree and, if logging, writes a CSV row. Connected to ``CanWorker.signals.frame_received``.

		Args:
			frame (Frame): The raw frame received off the bus.
		"""
		decoded = self.can.decode(frame) if self.can is not None else None
		self.canLogs.update_tree(frame, self.channel, decoded)

		if self.log_writer is not None:
			self.log_writer.writerow([
				# .astimezone() attaches the local tzinfo without changing the
				# displayed time - CSV timestamps are meant to read as local
				# wall-clock time, not UTC.
				datetime.now().astimezone().isoformat(timespec="milliseconds"),
				self.channel,
				f"0x{frame.id:X}",
				frame.dlc,
				frame.data.hex(" "),
				"; ".join(f"{name}={value}" for name, value in decoded.items()) if decoded is not None else "",
			])

	def start_logging(self) -> None:
		"""Opens a file picker and starts writing received frames to a CSV file.

		Each row logged by :meth:`_on_frame_received` while logging is active
		has the columns written here as its header. No-op if the dialog is
		cancelled.
		"""
		log_path, _ = QFileDialog.getSaveFileName(
			self,
			"Start Logging",
			"",
			"CSV Files (*.csv)"
		)

		if not log_path:
			return

		# Deliberately not a `with` block: the file must stay open across
		# separate calls (_on_frame_received writes to it as frames arrive,
		# stop_logging closes it later), not just for this method's duration.
		self.log_file = open(log_path, "w", newline="", encoding="utf-8")  # noqa: SIM115
		self.log_writer = csv.writer(self.log_file)
		self.log_writer.writerow(["Timestamp", "Channel", "ID", "DLC", "Data", "Decoded"])

		self.action_Start_Logging.setEnabled(False)
		self.actionSto_p_Logging.setEnabled(True)

	def stop_logging(self) -> None:
		"""Closes the CSV log file, if logging is active."""
		if self.log_file is not None:
			self.log_file.close()
		self.log_file = None
		self.log_writer = None

		self.action_Start_Logging.setEnabled(True)
		self.actionSto_p_Logging.setEnabled(False)

	def closeEvent(self, event):
		"""Stops any running worker and closes the log file before the window closes.

		Args:
			event (QCloseEvent): The close event to accept once cleanup is done.
		"""
		if self.stop_event is not None:
			self.stop_event.set()

		self.thread_pool.waitForDone()
		self.stop_logging()

		event.accept()
