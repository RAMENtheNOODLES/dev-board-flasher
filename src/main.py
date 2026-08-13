import gc
import sys
import ctypes
import os
from PySide6.QtCore import QIODevice, QEvent, QSettings, QCoreApplication, Qt
from PySide6.QtWidgets import QApplication, QMainWindow, QFileDialog, QSplashScreen, QProgressBar, QLabel
from PySide6.QtSerialPort import QSerialPortInfo, QSerialPort
from PySide6.QtGui import QDragEnterEvent, QDragLeaveEvent, QDropEvent, QFont, QFontDatabase, QIcon, QPixmap, QPalette, QColor

from utils.wiz_utils import WizLogger, get_config_path, Updater, StoredSettings
import logging
import logging.config
from utils.board_utils import BoardConfigurer

from pathlib import Path

import tomllib

# Import the auto-generated UI classes created by the Makefile
from ui_main_window import Ui_MainWindow
from github_token_ui import GithubTokenUI
from remote_configs import RemoteConfigs

import fonts_rc

# Sentinel exit code the app.exec() loop in __main__ watches for to relaunch
# MainWindow in-process instead of exiting (e.g. after Edit > Reload App, or
# after picking a new external board/tool directory).
EXIT_CODE_RESTART = -523904

class AdvancedSplashScreen(QSplashScreen):
	"""Splash screen shown while :meth:`MainWindow.load` runs its startup tasks.

	Displays the app version and a progress bar that advances as each
	startup task in :meth:`MainWindow.load`'s ``load_tasks`` list completes.
	"""

	def __init__(self, pixmap):
		"""Builds the version label and progress bar over ``pixmap``.

		Args:
			pixmap (QPixmap): Background image the splash screen is shown
				over (the app logo).
		"""
		super().__init__(pixmap)

		self.label = QLabel(self)
		config_path = get_config_path()
		
		with open(config_path, "rb") as f:
			self.config = tomllib.load(f)
			self.ver = self.config["project"]["version"]
			self.label.setText(f"v{self.ver}")

		font = QFont()
		font.setPointSize(20)

		self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
		self.label.setFont(font)
		palette = self.label.palette()
		palette.setColor(QPalette.ColorGroup.All, QPalette.ColorRole.WindowText, QColor("white"))
		self.label.setPalette(palette)

		# Setup progress bar
		self.progress_bar = QProgressBar(self)
		margin = 10
		pb_height = 20
		progress_bar_y = pixmap.height() - pb_height - margin
		self.progress_bar.setGeometry(
			margin,
			progress_bar_y,
			pixmap.width() - (margin * 2),
			pb_height
		)
		self.progress_bar.setRange(0, 100)

		# Position the version label directly above the progress bar
		label_height = 30
		self.label.setGeometry(0, progress_bar_y - label_height, pixmap.width(), label_height)
		self.progress_bar.setValue(0)
		self.progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)

	def update_progress(self, current_step, total_steps, message):
		"""Calculates progress percentage dynamically based on current step.

		Args:
			current_step (int): Index (1-based) of the startup task that just
				started.
			total_steps (int): Total number of startup tasks.
			message (str): Status text shown below the progress bar.
		"""
		percentage = int((current_step / total_steps) * 100)
		self.progress_bar.setValue(percentage)
		self.showMessage(message, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter, Qt.GlobalColor.black)
		
		# Keep GUI responsive while tasks execute
		QApplication.processEvents()

class MainWindow(QMainWindow, Ui_MainWindow):
	"""Main application window for the dev board flasher.

	Wires together the generated Qt UI, the board configuration cache, and
	the serial port/monitor controls, and handles drag-and-drop of firmware
	files onto the window. The selected board, flash tool settings preset,
	baud rate, firmware file, and remote config list are persisted via
	:class:`StoredSettings` and restored the next time the app is launched.

	Attributes:
		configurer (BoardConfigurer): Discovers and caches available board
			configurations.
		flash_file (str): Path to the firmware file currently selected for
			upload.
		serial (QSerialPort): Serial port used for flashing and the serial
			monitor.
	"""

	def __init__(self):
		"""Initializes the main window and defers the rest of startup to :meth:`load`.

		Binds the generated Qt UI (``setupUi``), then shows an
		:class:`AdvancedSplashScreen` while :meth:`load` runs the startup
		tasks (fonts, board discovery, signal wiring, restoring cached
		settings, and the update check) in the background.
		"""
		super().__init__()
		self.logger = logging.getLogger(__name__)
		self.setupUi(self) # Binds the primary main window layout
		self.logger = logging.getLogger(__name__)
		self.load()

	def open_github_token_ui(self):
		"""Opens the modal dialog for viewing/setting the stored GitHub personal access token."""
		self.token_ui = GithubTokenUI(self)
		self.token_ui.exec()

	def open_remote_configs_ui(self):
		"""Opens the modal dialog for managing the list of remote board/flashing-tool configs.

		On acceptance, the updated list is persisted to
		:data:`StoredSettings.REMOTE_CONFIGS`; picking up the change
		requires restarting the app (**Edit > Reload App**).
		"""
		self.remote_configs_ui = RemoteConfigs(self)
		self.remote_configs_ui.exec()

	def update_selected_board(self):
		"""Updates the currently selected board from the board select dropdown.

		Reads the current index of ``boardSelect`` and stores the matching
		:class:`BoardConfig` on ``self.selected_board``, repopulates
		``flashToolSettings`` with the newly selected board's flasher's
		available settings presets (from
		:meth:`~utils.flashing_tools.base_flashing_tool.BaseFlashingTool.get_settings`),
		restoring the previously chosen preset from
		:data:`StoredSettings.CHOSEN_TOOL_SETTING`, persists the new board
		index to :data:`StoredSettings.CHOSEN_BOARD`, then re-evaluates
		whether the upload button should be enabled.
		"""
		board_idx = self.boardSelect.currentIndex()
		self.selected_board = self.configurer.get_board_cache()[board_idx]
		# update flash tool settings
		tool_settings = StoredSettings.CHOSEN_TOOL_SETTING.get()
		self.logger.debug(f"Chosen tool setting IDX: {tool_settings}")

		self.flashToolSettings.clear()
		if self.selected_board is not None:
			settings = self.selected_board.Flasher.get_settings()
			self.logger.debug(f"Updating board settings: {settings}")
			self.flashToolSettings.addItems(settings)
			self.flashToolSettings.setCurrentIndex(int(tool_settings))

			StoredSettings.CHOSEN_BOARD.set(board_idx)
			self.logger.debug(f"Setting chosen board idx: {board_idx}")
		self.check_can_upload()

	def check_for_updates_btn(self):
		"""Checks GitHub for a newer release and, if the user accepts, downloads and installs it."""
		self.logger.info("Checking for updates")
		self.updater.check_for_updates_and_install()

	def eventFilter(self, watched, event):
		"""Handles window resize events to keep overlay widgets in sync.

		Args:
			watched: The object being watched by this event filter.
			event (QEvent): The event to process.

		Returns:
			bool: The result of the base class's event filter handling.
		"""
		# When the window scales, resize the overlay to fill the screen
		if event.type() == QEvent.Type.Resize:
			self.vignette.resize(self.size())
			self.vignette.move(0, 0)
			self.containerWidget.resize(self.centralWidget().size())
			self.actualWidget.resize(self.centralWidget().size())
		return super().eventFilter(watched, event)

	def dragEnterEvent(self, event: QDragEnterEvent):
		"""Shows the drop-target overlay when a file is dragged over the window.

		Args:
			event (QDragEnterEvent): The drag-enter event containing the
				dragged mime data.
		"""
		if event.mimeData().hasUrls():
			event.acceptProposedAction()
			self.vignette.show()

	def dragLeaveEvent(self, event: QDragLeaveEvent):
		"""Hides the drop-target overlay when a drag leaves the window.

		Args:
			event (QDragLeaveEvent): The drag-leave event.
		"""
		self.vignette.hide()

	def dropEvent(self, event: QDropEvent):
		"""Handles a file being dropped onto the window.

		Selects the first dropped file as the firmware file to upload,
		updates the UI to reflect the new selection, and persists it to
		:data:`StoredSettings.CACHED_FILE_TO_FLASH`.

		Args:
			event (QDropEvent): The drop event containing the dropped mime
				data.
		"""
		self.vignette.hide()
		if event.mimeData().hasUrls():
			files = [url.toLocalFile() for url in event.mimeData().urls()]
			self.logger.debug("Dropped files:", files)
			# Update any labels or fields you designed here
			self.flash_file = files[0]

			self.fileName.setText(self.flash_file)
			StoredSettings.CACHED_FILE_TO_FLASH.set(self.flash_file)
			self.check_can_upload()

	def browse_files(self):
		"""Opens a file picker dialog for selecting a firmware file to upload.

		Defaults to the previously selected file, if any. Updates the file
		name label, persists the selection to
		:data:`StoredSettings.CACHED_FILE_TO_FLASH`, and re-evaluates
		whether the upload button should be enabled.
		"""
		board = self.configurer.get_board_cache()[self.boardSelect.currentIndex()]

		allowed_files = ""
		if board is not None:
			for file in board.SupportedFiles:
				allowed_files += file + " "

		allowed_files = allowed_files.rstrip()

		self.flash_file, _ = QFileDialog.getOpenFileName(
			self,
			"Open File",
			self.flash_file,
			f"Binary Files ({allowed_files});; All Files (*)"
		)

		if self.flash_file:
			self.fileName.setText(self.flash_file)
			StoredSettings.CACHED_FILE_TO_FLASH.set(self.flash_file)

			self.logger.debug(f"File ready for upload: {self.flash_file}")

		self.check_can_upload()

	def check_can_upload(self) -> bool:
		"""Determines whether an upload can currently be started.

		Upload is disabled when no serial port is selected, no file has
		been chosen, or the serial monitor connection is open. Updates the
		enabled state of the upload button as a side effect.

		Returns:
			bool: True if an upload can be started, False otherwise.
		"""
		if ((self.fileName.text() == "") or (self.serial.isOpen())):
			self.uploadBoardButton.setEnabled(False)
			return False
		else:
			self.uploadBoardButton.setEnabled(True)
			return True

	def upload_to_board(self):
		"""Flashes the selected firmware file to the currently selected board.

		Resolves the board's flashing tool from the cache, points it at the
		shared log box, and invokes its flash routine on the chosen serial
		port and file, using the settings preset chosen in
		``flashToolSettings``. No-op if uploading is not currently allowed.
		"""
		if (not self.check_can_upload()):
			return

		board = self.configurer.get_board_cache()[self.boardSelect.currentIndex()]

		if board is not None:
			board.Flasher.set_log_box(self.logText)
			board.Flasher.set_progress_bar(self.progressBar)

			self.uploadBoardButton.setEnabled(False)
			board.Flasher.flash(board, self.serialPortsBox.currentText(), self.flash_file, self.flashToolSettings.currentText())
			self.uploadBoardButton.setEnabled(True)

	def toggle_connection(self):
		"""Opens or closes the connection depending on current state."""
		if not self.serial.isOpen():
			# Set the destination port name (e.g. COM3 or /dev/ttyUSB0)
			self.serial.setPortName(self.serialPortsBox.currentText())
			self.serial.setBaudRate(int(self.baudRateBox.currentText()))
			
			# Attempt to claim port access in standard Read/Write configuration
			if self.serial.open(QIODevice.OpenModeFlag.ReadWrite):
				self.uploadBoardButton.setEnabled(False)
				self.serialMonitorButton.setText("Disconnect")
				self.logText.append(f"--- Port: {self.serial.portName()} ---")
				self.logText.append(f"--- Baud: {self.serial.baudRate()} ---")
				self.logText.append("--- Connected Successfully ---")
			else:
				self.logText.append(f"--- Connection Failed: {self.serial.errorString()} ---")
		else:
			self.uploadBoardButton.setEnabled(True)
			self.serial.close()
			self.serialMonitorButton.setText("Connect")
			self.logText.append("--- Disconnected ---")

	def read_serial_data(self):
		"""Triggers automatically when microcontrollers stream text data."""
		# Read all payload bytes currently waiting inside the serial buffer
		data = self.serial.readAll()
		# Decode binary stream into universal readable text format
		raw_text = data.data()
		text = bytes(raw_text).decode('utf-8', errors='replace')
		
		# Shift visual view downward so new entries stay visible
		cursor = self.logText.textCursor()
		cursor.movePosition(cursor.MoveOperation.End)
		self.logText.setTextCursor(cursor)
		self.logText.insertPlainText(text)

	def send_serial_data(self):
		"""Pushes string strings down to the connected microchip hardware."""
		if self.serial.isOpen():
			text_to_send = self.serialTXBox.text()
			if text_to_send:
				# Add line ending suffix expected by microcontrollers (\r\n)
				full_payload = text_to_send + "\r\n"
				self.serial.write(full_payload.encode('utf-8'))
				self.serialTXBox.clear()
		else:
			self.logText.append("--- Cannot Send: Port is closed ---")

	def refresh_serial_ports(self):
		"""Repopulates the serial port dropdown with currently available ports."""
		ports = QSerialPortInfo.availablePorts()

		self.serialPortsBox.clear()
		
		for port in ports:
			self.serialPortsBox.addItem(port.portName())
			self.logger.debug(f"Port Name: {port.portName()}")
			self.logger.debug(f"Description: {port.description()}")
			self.logger.debug(f"Manufacturer: {port.manufacturer()}")
			self.logger.debug("-" * 20)

	def handle_serial_error(self, error: QSerialPort.SerialPortError):
		"""Reacts to errors reported by the serial port connection.

		Disconnects the serial monitor when the device is unplugged or an
		unexpected error occurs; ignores benign "not open"/"no error"
		states.

		Args:
			error (QSerialPort.SerialPortError): The error reported by the
				serial port.
		"""
		if error == QSerialPort.SerialPortError.ResourceError:
			self.logger.error("Device was disconnected...")
			self.toggle_connection()
		elif error in [QSerialPort.SerialPortError.NotOpenError, QSerialPort.SerialPortError.NoError]:
			pass
		else:
			self.logger.error(f"Error: {error}")
			self.toggle_connection()

	def load(self):
		"""Runs startup behind an :class:`AdvancedSplashScreen`, then shows the window.

		Executes ``load_tasks`` in order (fonts, board configuration, signal
		wiring, restoring cached settings, misc window setup, then the
		update check), advancing the splash screen's progress bar after
		each one, before showing the main window and closing the splash
		screen.
		"""
		# setup splash screen
		pixmap = QPixmap(":/logo.png")
		splash = AdvancedSplashScreen(pixmap)
		splash.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.SplashScreen)
		splash.show()

		# Set icon
		self.setWindowIcon(QIcon(":/logo.png"))

		QCoreApplication.setOrganizationDomain("CookieJAR")
		QCoreApplication.setApplicationName("wizlog")

		load_tasks = [
			(self.init_fonts, "Initializing Fonts..."),
			(self.configure_boards, "Configuring Boards..."),
			(self.connect_functions, "Connecting functions to event triggers..."),
			(self.get_cached_settings, "Loading cached settings..."),
			(self.misc, "Misc..."),
			(self.check_for_updates, "Checking for updates...")
		]

		total_tasks = len(load_tasks)

		for index, (task_function, message) in enumerate(load_tasks):
			step_number = index + 1
			splash.update_progress(step_number, total_tasks, message)

			task_function()

		self.show()
		splash.finish(self)
		self.activateWindow()

	def init_fonts(self):
		"""Loads the bundled Nerd Font and applies it as the app's global font."""
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

	def configure_boards(self):
		"""Builds the board cache (local + :data:`StoredSettings.REMOTE_CONFIGS`) and populates the board dropdown."""
		self.configurer = BoardConfigurer(StoredSettings.REMOTE_CONFIGS.get([]))
		self.flash_file = ""
		self.serial = QSerialPort()
		self.updater = Updater()

		self.boardSelect.addItems([board_name.BoardName for board_name in self.configurer.get_board_cache() if board_name is not None])

	def connect_functions(self):
		"""Wires all UI signals (menu actions, buttons, serial events) to their handlers."""
		self.boardSelect.currentIndexChanged.connect(self.update_selected_board)
		self.uploadButton.clicked.connect(self.browse_files)
		self.actionOpen_File.triggered.connect(self.browse_files)
		self.uploadBoardButton.clicked.connect(self.upload_to_board)
		self.refreshCOMPortButton.clicked.connect(self.refresh_serial_ports)
		self.serialMonitorButton.clicked.connect(self.toggle_connection)
		self.serial.readyRead.connect(self.read_serial_data)
		self.clearLogsButton.clicked.connect(lambda: self.logText.clear())
		self.sendTXDataButton.clicked.connect(self.send_serial_data)
		self.serialTXBox.returnPressed.connect(self.send_serial_data)
		self.serial.errorOccurred.connect(self.handle_serial_error)
		self.baudRateBox.currentIndexChanged.connect(lambda: StoredSettings.CHOSEN_BAUD_RATE.set(self.baudRateBox.currentIndex()))
		self.flashToolSettings.currentIndexChanged.connect(lambda: StoredSettings.CHOSEN_TOOL_SETTING.set(self.flashToolSettings.currentIndex()))
		self.actionGithubPAT.triggered.connect(self.open_github_token_ui)
		self.actionRemote_Configurations.triggered.connect(self.open_remote_configs_ui)

		self.action_Reload_App.triggered.connect(lambda: QApplication.exit(EXIT_CODE_RESTART))

		self.actionCheck_for_Updates.triggered.connect(self.check_for_updates_btn)

	def get_cached_settings(self):
		"""Restores the previously selected board, firmware file, and baud rate from :class:`StoredSettings`."""
		board = StoredSettings.CHOSEN_BOARD.get()
		self.logger.debug(f"Chosen Board IDX: {board}")
		if (board != ""):
			self.boardSelect.setCurrentIndex(int(board))

		self.update_selected_board()

		file_path_str = StoredSettings.CACHED_FILE_TO_FLASH.get()
		if (file_path_str != ""):
			self.flash_file = str(Path(file_path_str).resolve()).replace("\\", "/")
		else:
			self.flash_file = ""

		self.fileName.setText(self.flash_file)

		# pick chosen baud_rate
		br = StoredSettings.CHOSEN_BAUD_RATE.get()

		self.logger.debug(f"Chosen buad rate IDX: {br}")

		if (br != ""):
			self.baudRateBox.setCurrentIndex(int(br))

	def check_for_updates(self):
		"""Reads the app version from ``pyproject.toml``, shows it, and checks GitHub for an update."""
		config_path = get_config_path()

		with open(config_path, "rb") as f:
			self.config = tomllib.load(f)
			self.ver = self.config["project"]["version"]
			self.versionLabel.setText(f"v{self.ver}")
			self.check_for_updates_btn()

	def misc(self):
		"""Handles the remaining one-off startup steps that don't fit the other load tasks."""
		self.refresh_serial_ports()
		self.vignette.raise_()
		self.installEventFilter(self)
		self.logText.clear()
		self.logText.setFontPointSize(8)
		self.check_can_upload()

if __name__ == "__main__":
	app = QApplication(sys.argv)
	logging.config.dictConfig(WizLogger.LOGGING_CONFIG)

	logger = logging.getLogger(__name__)

	reload_attempt = 0

	while True:
		if reload_attempt >= 5:
			logger.critical("Application tried restarting too many times. Exiting...")
			sys.exit(-1)

		logger.info("Started main app...")
		with open(get_config_path(), "rb") as f:
			config = tomllib.load(f)
			ver = config["project"]["version"]

		logger.info(f"Version {ver}")
		
		if os.name == 'nt':
			appid = f"cookiejar.uploadwiz.{ver}" # Custom unique string
			ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(appid)

		try:
			window = MainWindow()

			exit_code = app.exec()

			window.close()
			del window

			if exit_code != EXIT_CODE_RESTART:
				sys.exit(exit_code)
		except Exception as e:
			logger.exception("Unknown exception has occurred...")
			reload_attempt += 1
		finally:
			gc.collect()
		
		logger.info("Reloading Application...")
