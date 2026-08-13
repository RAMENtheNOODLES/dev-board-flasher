from PySide6.QtWidgets import QFileDialog, QMainWindow, QMessageBox
from PySide6.QtCore import Qt, QCoreApplication, QTimer
from PySide6.QtGui import QFontDatabase, QIcon, QFont
from ui_can import Ui_CANViewer

from utils.wiz_utils.stored_settings import StoredSettings

from tools.can import CAN

import logging

class CANViewer(QMainWindow, Ui_CANViewer):
	def __init__(self) -> None:
		super().__init__()

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
			self.logger.info("Done Initilaizing Fonts")
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

		self.timer = QTimer(self)
		self.timer.timeout.connect(self.receive_loop)
		self.action_Load_DBC.triggered.connect(self.load_dbc)
		self.deviceSelect.currentIndexChanged.connect(self.populate_channels)
		self.deviceSelect.currentIndexChanged.connect(self.selected_device)
		self.connectButton.clicked.connect(self.connect_can)
		self.channelSelect.currentIndexChanged.connect(self.selected_channel)

		self.selected_device(0)
		self.selected_channel(0)

		self.dbc_file = StoredSettings.CAN_DBC_FILE.get(None)

	def populate_devices(self):
		self.deviceSelect.clear()
		for dev, serial, channels in CAN.list_devices_with_channels():
			self.deviceSelect.addItem(f"{dev} : {serial}", channels)

	def populate_channels(self):
		self.channelSelect.clear()
		for channel in self.deviceSelect.currentData():
			self.channelSelect.addItem(f"Channel: {channel}")

	def selected_device(self, index):
		self.dev = CAN.list_devices()[index]

	def selected_channel(self, index):
		self.channel = index

	def load_dbc(self):
		self.dbc_file, _ = QFileDialog.getOpenFileName(
			self,
			"Open File",
			StoredSettings.CAN_DBC_FILE.get(""),
			f"CAN Database Files (*.dbc)"
		)

		StoredSettings.CAN_DBC_FILE.set(self.dbc_file)

	def connect_can(self):
		if self.can is not None and self.can.is_open:
			self.can.close()
			self.timer.stop()
			self.connectButton.setText("Connect")
			return

		self.can = CAN(self.dev, self.channel, self.dbc_file)

		self.connectButton.setText("Disconnect")
		self.can.open()
		self.timer.start(20)

	def receive_loop(self):
		if self.can is not None and self.can.is_open:
			msg = self.can.receive()

			if msg is not None:
				self.logger.debug(f"CAN msg: {msg.get(data)}")
				self.canLogs.appendPlainText(f"{msg}\n")
		else:
			self.timer.stop()
