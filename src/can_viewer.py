import logging
import threading

from PySide6.QtCore import QCoreApplication, QTimer, QThreadPool
from PySide6.QtGui import QFontDatabase, QIcon, QFont
from PySide6.QtWidgets import QFileDialog, QMainWindow, QMessageBox
from canlib import Device
from canlib.canlib.enums import Bitrate
from canlib.frame import Frame

from tools.can import CAN
from ui_can import Ui_CANViewer
from utils.wiz_utils.can_worker import CanWorker
from utils.wiz_utils.stored_settings import StoredSettings


class CANViewer(QMainWindow, Ui_CANViewer):
	"""Standalone window for connecting to a Kvaser CAN device and viewing/decoding traffic.

	Opened via **Tools > CAN** (see :meth:`main.MainWindow.open_can_viewer`),
	which reuses a single instance across shows rather than recreating it.
	Device/channel selection and bus connect/disconnect run on a dedicated
	:class:`~PySide6.QtCore.QThreadPool` through :class:`CanWorker`, so the
	blocking CANlib calls don't freeze this window's UI thread.
	"""

	_CAN_SAMPLE_RATE: int = 100
	_BIT_RATES = [Bitrate.BITRATE_125K, Bitrate.BITRATE_250K, Bitrate.BITRATE_500K, Bitrate.BITRATE_1M]

	def __init__(self, parent = None) -> None:
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
		QCoreApplication.setApplicationName("wizlog")

		# init CAN
		try:
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

		# configure function connections
		self.can = None
		# Dedicated pool, not QThreadPool.globalInstance(): closeEvent()
		# blocks on waitForDone(), and the global pool also runs the main
		# window's long-lived USB_Monitor worker, which would make closing
		# this window hang until the whole app exits.
		self.thread_pool = QThreadPool(self)
		self.worker: CanWorker | None = None
		self.stop_event: threading.Event | None = None

		self.device_check_timer = QTimer(self)
		self.device_check_timer.timeout.connect(self.populate_devices)
		self.action_Load_DBC.triggered.connect(self.load_dbc)
		self.deviceSelect.currentIndexChanged.connect(self.populate_channels)
		self.deviceSelect.currentIndexChanged.connect(self.selected_device)
		self.connectButton.clicked.connect(self.connect_can)
		self.channelSelect.currentIndexChanged.connect(self.selected_channel)

		self.dbc_file = StoredSettings.CAN_DBC_FILE.get(None)

		self.selected_device(0)
		self.selected_channel(0)

	def populate_devices(self):
		self.deviceSelect.clear()
		for dev, serial, channels in CAN.list_devices_with_channels():
			self.deviceSelect.addItem(f"{dev} : {serial}", channels)

	def populate_channels(self):
		self.channelSelect.clear()
		channels = self.deviceSelect.currentData()
		if channels is not None:
			for channel in channels:
				self.channelSelect.addItem(f"Channel: {channel}")

	def selected_device(self, index):
		self.dev = CAN.list_devices()[index]
		if self.can is None and self.dev is not None:
			self.can = CAN(self.dev, 0, self.dbc_file, self._BIT_RATES[self.baudRateComboBox.currentIndex()])
		else:
			# These should not be none due to the if statement above
			assert self.can is not None
			assert self.dev is not None

			self.can.set_channel(0)
			self.can.set_device(self.dev)
			self.can.set_bitrate(self._BIT_RATES[self.baudRateComboBox.currentIndex()])

	def selected_channel(self, index):
		self.channel = index
		if self.can is not None:
			self.can.set_channel(index)

	def load_dbc(self):
		dbc_file, _ = QFileDialog.getOpenFileName(
			self,
			"Open File",
			StoredSettings.CAN_DBC_FILE.get(""),
			f"CAN Database Files (*.dbc)"
		)

		if not dbc_file:
			return

		self.dbc_file = dbc_file
		StoredSettings.CAN_DBC_FILE.set(self.dbc_file)

		if self.can is not None:
			# Walking the loaded DBC's messages/signals is slow enough that
			# it belongs off the GUI thread (see CanWorker.run), so the tree
			# itself only refreshes on the next connect rather than here.
			self.can.load_dbc(self.dbc_file)

	def connect_can(self):
		if self.worker is not None and self.stop_event is not None:
			# Already connected/connecting: ask the worker to close the
			# channel and stop, rather than touching it from this thread.
			self.connectButton.setEnabled(False)
			self.connectButton.setText("Disconnecting...")
			self.stop_event.set()
			return

		if self.can is None and self.dev is not None:
			self.can = CAN(self.dev, self.channel, self.dbc_file, self._BIT_RATES[self.baudRateComboBox.currentIndex()])

		# This should never be none due to the if statement above
		assert self.can is not None

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
		self.deviceSelect.setEnabled(enabled)
		self.channelSelect.setEnabled(enabled)
		self.baudRateComboBox.setEnabled(enabled)
		self.action_Load_DBC.setEnabled(enabled)

	def _on_can_connected(self):
		self.connectButton.setEnabled(True)
		self.connectButton.setText("Disconnect")

	def _on_can_disconnected(self):
		self.worker = None
		self.stop_event = None
		self.connectButton.setEnabled(True)
		self.connectButton.setText("Connect")
		self._set_controls_enabled(True)

	def _on_can_error(self, message: str):
		self.logger.error(f"CAN error: {message}")
		QMessageBox.critical(self, "CAN Error", message)

	def _on_frame_received(self, msg):
		if isinstance(msg, Frame):
			self.logger.debug(f"CAN msg: {msg.data.hex(" ", 4)}")
			self.canLogs.update_tree(msg.id)
		else:
			self.logger.debug(f"CAN msg: {msg.get("data")}")

	def closeEvent(self, event):
		if self.stop_event is not None:
			self.stop_event.set()

		self.thread_pool.waitForDone()

		event.accept()
