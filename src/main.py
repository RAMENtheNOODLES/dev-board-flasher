import ctypes
import gc
import logging
import logging.config
import os
import sys
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import tomllib
from PySide6.QtCore import QCoreApplication, QEvent, QIODevice, Qt, QThreadPool
from PySide6.QtGui import (
	QColor,
	QDragEnterEvent,
	QDragLeaveEvent,
	QDropEvent,
	QFont,
	QFontDatabase,
	QIcon,
	QPalette,
	QPixmap,
)
from PySide6.QtSerialPort import QSerialPort, QSerialPortInfo
from PySide6.QtWidgets import (
	QApplication,
	QFileDialog,
	QLabel,
	QMainWindow,
	QMessageBox,
	QProgressBar,
	QSplashScreen,
)

from can_viewer import CANViewer
from elf_viewer import ELFViewer
from github_token_ui import GithubTokenUI
from remote_configs import RemoteConfigs

# Import the auto-generated UI classes created by the Makefile
from ui_main_window import Ui_MainWindow
from utils.board_utils import BoardConfigurer
from utils.wiz_utils import (
	CacheHelper,
	GithubToken,
	PlainRunnable,
	StoredSettings,
	Updater,
	USBWorker,
	WizLogger,
	get_config_path,
)

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
		self.load()

	#region Event Functions

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
		tool_settings = StoredSettings.CHOSEN_TOOL_SETTING.get(0)
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
		"""Checks GitHub for a newer release and, if the user accepts, downloads and installs it.

		Unlike the silent check run at startup (see :meth:`check_for_updates`),
		this is wired to **Help > Check for Updates**, so it also tells the
		user when they're already up to date rather than doing nothing.
		"""
		self.logger.info("Checking for updates")
		update = self.updater.check_for_updates_and_install()

		if not update:
			QMessageBox.information(self, "No Update Available...", "There are currently no updates available...")

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
			self.logger.debug(f"Dropped files: {files}")
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
			StoredSettings.CACHED_FILE_TO_FLASH.get(StoredSettings.get_documents_path()),
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
		"""Opens or closes the serial monitor connection depending on current state.

		Uses the port and baud rate currently selected in ``serialPortsBox``/
		``baudRateBox``; status messages are appended to ``logText``.
		"""
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
		"""Reads any buffered serial input and appends it to the log box.

		Connected to the serial port's ``readyRead`` signal.
		"""
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
		"""Sends the text in ``serialTXBox`` to the board over the open serial port.

		Appends a ``\\r\\n`` line ending, then clears the input box. No-op
		(besides logging) if the port isn't open.
		"""
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

	def open_can_viewer(self):
		"""Shows the CAN viewer window, creating it (and wiring it to USB events) on first use.

		The same :class:`CANViewer` instance is reused across shows rather
		than being recreated each time, so an active connection/loaded DBC
		survives closing and reopening the window.
		"""
		if self.canViewer is None:
			self.canViewer = CANViewer(self)
			worker, _ = self.workers["USB_Monitor"]
			worker = cast(USBWorker, worker)
			worker.signals.device_connected.connect(self.canViewer.populate_devices)
			worker.signals.device_disconnected.connect(self.canViewer.populate_devices)

		self.canViewer.show()
		self.canViewer.activateWindow()

	def open_elf_viewer(self):
		if self.elfViewer is None:
			self.elfViewer = ELFViewer(self)
		
		self.elfViewer.show()
		self.elfViewer.activateWindow()

	def show_about(self):
		"""Shows the **Help > About** dialog with the app's version and credits."""
		QMessageBox.about(
			self,
			"About FlashWiz",
			f"""<h3> FlashWiz {self.versionLabel.text()} </h3>
			<p> Copyright © 2026. Built with PySide6.</p>
			<p> Designed by Carter Rommelfanger</p>"""
		)

	def closeEvent(self, event):
		"""Signals background workers to stop and closes any other open windows before exiting.

		Args:
			event (QCloseEvent): The close event to accept once cleanup is done.
		"""
		for worker, _ in self.workers.values():
			worker.stop_event.set()

		self.thread_pool.waitForDone()

		for window in QApplication.topLevelWidgets():
			if window != self:  # Avoid closing yourself twice
				window.close()

		event.accept()

	def clear_all_settings_btn(self):
		"""Handles **Tools > Clear All Settings**: confirms, then wipes every stored setting.

		Doesn't restart the app, since the wiped values are only re-read the
		next time each is fetched (e.g. next launch), not held in memory.
		"""
		resp = QMessageBox.critical(
			self, 
			"Confirm", 
			"Are you sure you want to clear ALL settings?",
			QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
			QMessageBox.StandardButton.Cancel
		)

		if resp == QMessageBox.StandardButton.Yes:
			StoredSettings.clear_all_settings()

	def invalidate_cache_btn(self):
		"""Handles **Edit > Invalidate Cache**: confirms, then clears the board and GitHub response caches.

		Restarts the app (via ``EXIT_CODE_RESTART``) afterward, since the
		board cache is only rebuilt as part of :meth:`configure_boards`
		during startup.
		"""
		resp = QMessageBox.critical(
			self, 
			"Confirm", 
			"Are you sure you want to invalidate the cache?",
			QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
			QMessageBox.StandardButton.Cancel
		)
		
		if resp == QMessageBox.StandardButton.Yes:
			CacheHelper.invalidate_cache()
			GithubToken.clear_cache()
			QApplication.exit(EXIT_CODE_RESTART)

	#endregion

	#region Load Functions

	def load(self):
		"""Runs startup behind an :class:`AdvancedSplashScreen`, then shows the window.

		Executes ``load_tasks`` in order (migrating legacy registry settings
		to the settings file, fonts, board configuration, signal wiring,
		restoring cached settings, misc window setup, background workers,
		then the update check), advancing the splash screen's progress bar
		after each one, before showing the main window and closing the
		splash screen.
		"""
		# setup splash screen
		pixmap = QPixmap(":/logo.png")
		splash = AdvancedSplashScreen(pixmap)
		splash.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.SplashScreen)
		splash.show()

		# Set icon
		self.setWindowIcon(QIcon(":/logo.png"))

		QCoreApplication.setOrganizationDomain("CookieJAR")
		QCoreApplication.setApplicationName("flashwiz")

		load_tasks = [
			(lambda: StoredSettings.transfer_settings_to_file(), "Transferring settings to file..."),
			(self.init_fonts, "Initializing Fonts..."),
			(self.configure_boards, "Configuring Boards..."),
			(self.connect_functions, "Connecting functions to event triggers..."),
			(self.get_cached_settings, "Loading cached settings..."),
			(self.check_for_optional_libraries, "Checking for optional settings..."),
			(self.misc, "Misc..."),
			(self.setup_background_workers, "Setting up background workers..."),
			(self.check_for_updates, "Checking for updates..."),
		]

		total_tasks = len(load_tasks)

		for index, (task_function, message) in enumerate(load_tasks):
			step_number = index + 1
			splash.update_progress(step_number, total_tasks, message)

			self.logger.debug(message)
			task_function()

		splash.showMessage("Done Loading App!", Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter, Qt.GlobalColor.black)

		self.logger.info("Done Loading App!")

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
			self.logger.info("Done Initializing Fonts")
		else:
			self.logger.error("Error: Could not load font from resources.")

	def configure_boards(self):
		"""Builds the board cache (local + :data:`StoredSettings.REMOTE_CONFIGS`) and populates the board dropdown."""
		self.configurer = BoardConfigurer(StoredSettings.REMOTE_CONFIGS.secure_get([]))
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
		self.action_About.triggered.connect(self.show_about)

		self.action_Reload_App.triggered.connect(lambda: QApplication.exit(EXIT_CODE_RESTART))
		self.actionClear_All_Settings.triggered.connect(self.clear_all_settings_btn)
		self.action_Invalidate_Cache.triggered.connect(self.invalidate_cache_btn)

		self.actionCheck_for_Updates.triggered.connect(self.check_for_updates_btn)
		self.actionCANLib_Kvaser.triggered.connect(self.open_can_viewer)

		self.action_Elf_Parser.triggered.connect(self.open_elf_viewer)

	def get_cached_settings(self):
		"""Restores the previously selected board, firmware file, and baud rate from :class:`StoredSettings`."""
		board = StoredSettings.CHOSEN_BOARD.get("")
		self.logger.debug(f"Chosen Board IDX: {board}")
		if (board != ""):
			self.boardSelect.setCurrentIndex(int(board))

		self.update_selected_board()

		file_path_str = StoredSettings.CACHED_FILE_TO_FLASH.get("")
		if (file_path_str != ""):
			self.flash_file = str(Path(file_path_str).resolve()).replace("\\", "/")
		else:
			self.flash_file = ""

		self.fileName.setText(self.flash_file)

		# pick chosen baud_rate
		br = StoredSettings.CHOSEN_BAUD_RATE.get("")

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
			self.logger.info("Checking for updates")

			force_update = "--force-update" in sys.argv

			self.updater.check_for_updates_and_install(force_update)

	def check_for_optional_libraries(self):
		"""Enables/disables **Tools > CAN** based on whether the Kvaser CANlib drivers are installed.

		``tools.can`` is imported lazily here rather than at module load time
		(see ``CAN.check_for_libraries``/``_canlib_can``), so a machine
		without the drivers can still run the rest of the app.
		"""
		from tools.can import CAN

		has_kvaser_libraries = CAN.check_for_libraries()

		self.actionCANLib_Kvaser.setEnabled(has_kvaser_libraries)

	def setup_background_workers(self):
		"""Starts the long-lived background workers (currently just USB device monitoring).

		Workers are tracked in ``self.workers`` (keyed by task id) so
		:meth:`closeEvent` can signal each one's ``stop_event`` before the
		app exits.
		"""
		# Thread Functions

		def startUSBWorker(thread: QThreadPool, worker: USBWorker) -> None:
			"""Wires a USBWorker's signals to refresh the serial port list, then starts it.

			Args:
				thread (QThreadPool): Pool to run ``worker`` on.
				worker (USBWorker): The worker to start.
			"""
			worker.signals.device_connected.connect(self.refresh_serial_ports)
			worker.signals.device_disconnected.connect(self.refresh_serial_ports)
			thread.start(worker)

		self.thread_pool = QThreadPool.globalInstance()

		self.workers: dict[str, tuple[PlainRunnable, Callable[[QThreadPool, Any], None]]] = {
			"USB_Monitor": (USBWorker("USB_Monitor", threading.Event()), startUSBWorker)
		}

		for (obj, setup_worker) in self.workers.values():
			setup_worker(self.thread_pool, obj)

	def misc(self):
		"""Handles the remaining one-off startup steps that don't fit the other load tasks."""
		self.canViewer = None
		self.elfViewer = None
		self.refresh_serial_ports()
		self.vignette.raise_()
		self.installEventFilter(self)
		self.logText.clear()
		self.logText.setFontPointSize(8)
		self.check_can_upload()

	#endregion

if __name__ == "__main__":
	app = QApplication(sys.argv)
	logging.config.dictConfig(WizLogger.LOGGING_CONFIG)
	logger = logging.getLogger(__name__)

	if os.name == 'nt':
		# Named mutex the installer looks for (AppMutex in scripts/installer.iss)
		# to detect this app is running and close it during a silent
		# self-update. Held open for the lifetime of this process; never closed
		# explicitly since the OS releases it on exit.
		_update_mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "Global\\FlashWizMutex")

		if not _update_mutex:
			error_code = ctypes.get_last_error()
			logger.critical(f"Failed to create mutex. Windows Error: {error_code}")
			sys.exit(error_code)

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
			appid = f"cookiejar.flashwiz.{ver}" # Custom unique string
			ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(appid)

		try:
			window = MainWindow()

			exit_code = app.exec()

			window.close()
			del window

			if exit_code != EXIT_CODE_RESTART:
				sys.exit(exit_code)
		except Exception:
			logger.exception("Unknown exception has occurred...")
			reload_attempt += 1
		finally:
			gc.collect()
		
		logger.info("Reloading Application...")
