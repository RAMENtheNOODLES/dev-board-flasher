import sys
from PySide6.QtCore import QIODevice, QTextStream, QEvent
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QFileDialog
from PySide6.QtSerialPort import QSerialPortInfo, QSerialPort
from PySide6.QtGui import QDragEnterEvent, QDragLeaveEvent, QDropEvent, QFont, QFontDatabase

from utils.board_utils import BoardConfigurer

# Import the auto-generated UI classes created by the Makefile
from ui_main_window import Ui_MainWindow

import fonts_rc


class MainWindow(QMainWindow, Ui_MainWindow):
	"""Main application window for the dev board flasher.

	Wires together the generated Qt UI, the board configuration cache, and
	the serial port/monitor controls, and handles drag-and-drop of firmware
	files onto the window.

	Attributes:
		configurer (BoardConfigurer): Discovers and caches available board
			configurations.
		file_name (str): Path to the firmware file currently selected for
			upload.
		serial (QSerialPort): Serial port used for flashing and the serial
			monitor.
	"""

	def __init__(self):
		"""Initializes the main window, loads UI resources, and wires up signals."""
		super().__init__()
		self.setupUi(self) # Binds the primary main window layout

		font_id = QFontDatabase.addApplicationFont(":/FiraCodeNerdFont-Regular.ttf")

		if font_id != -1:
			# 4. Extract the exact internal font family name
			font_family = QFontDatabase.applicationFontFamilies(font_id)[0]

			# 5. Create a font object and apply it globally to the app
			global_font = QFont(font_family, 12)  # Family name and default size
			self.setFont(global_font)
		else:
			print("Error: Could not load font from resources.")

		self.configurer = BoardConfigurer()
		self.file_name = ""
		self.serial = QSerialPort()

		self.boardSelect.addItems([board_name.BoardName for board_name in self.configurer.get_board_cache()])

		self.refresh_serial_ports()

		self.vignette.raise_()
		self.installEventFilter(self)
		
		self.uploadButton.clicked.connect(self.browse_files)
		self.actionOpen_File.triggered.connect(self.browse_files)
		self.uploadBoardButton.clicked.connect(self.upload_to_board)
		self.refreshCOMPortButton.clicked.connect(self.refresh_serial_ports)
		self.serialMonitorButton.clicked.connect(self.toggle_connection)
		self.serial.readyRead.connect(self.read_serial_data)
		self.clearLogsButton.clicked.connect(lambda: self.logText.clear())
		self.logText.clear()

		self.sendTXDataButton.clicked.connect(self.send_serial_data)
		self.serialTXBox.returnPressed.connect(self.send_serial_data)
		self.serial.errorOccurred.connect(self.handle_serial_error)

		self.check_can_upload()

	def update_selected_board(self):
		"""Updates the currently selected board from the board select dropdown.

		Reads the current index of ``boardSelect`` and stores the matching
		:class:`BoardConfig` on ``self.selected_board``, then re-evaluates
		whether the upload button should be enabled.
		"""
		self.selected_board = self.configurer.get_board_cache()[self.boardSelect.currentIndex()]
		self.check_can_upload()

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

		Selects the first dropped file as the firmware file to upload and
		updates the UI to reflect the new selection.

		Args:
			event (QDropEvent): The drop event containing the dropped mime
				data.
		"""
		self.vignette.hide()
		if event.mimeData().hasUrls():
			files = [url.toLocalFile() for url in event.mimeData().urls()]
			print("Dropped files:", files)
			# Update any labels or fields you designed here
			self.file_name = files[0]

			self.fileName.setText(self.file_name)
			self.check_can_upload()

	def browse_files(self):
		"""Opens a file picker dialog for selecting a firmware file to upload.

		Updates the file name label and re-evaluates whether the upload
		button should be enabled based on the selection.
		"""
		self.file_name, _ = QFileDialog.getOpenFileName(
			self,
			"Open File",
			"",
			"Binary Files (*.bin *.hex);; All Files (*)"
		)

		if self.file_name:
			self.fileName.setText(self.file_name)

			print(f"File ready for upload: {self.file_name}")

		self.check_can_upload()

	def check_can_upload(self) -> bool:
		"""Determines whether an upload can currently be started.

		Upload is disabled when no serial port is selected, no file has
		been chosen, or the serial monitor connection is open. Updates the
		enabled state of the upload button as a side effect.

		Returns:
			bool: True if an upload can be started, False otherwise.
		"""
		if ((self.serialPortsBox.currentText() == "") or (self.fileName.text() == "") or (self.serial.isOpen())):
			self.uploadBoardButton.setEnabled(False)
			return False
		else:
			self.uploadBoardButton.setEnabled(True)
			return True

	def upload_to_board(self):
		"""Flashes the selected firmware file to the currently selected board.

		Resolves the board's flashing tool from the cache, points it at the
		shared log box, and invokes its flash routine on the chosen serial
		port and file. No-op if uploading is not currently allowed.
		"""
		if (not self.check_can_upload()):
			return

		board = self.configurer.get_board_cache()[self.boardSelect.currentIndex()]

		board.Flasher.set_log_box(self.logText)

		self.uploadBoardButton.setEnabled(False)
		board.Flasher.flash(board, self.serialPortsBox.currentText(), self.file_name)
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
			print(f"Port Name: {port.portName()}")
			print(f"Description: {port.description()}")
			print(f"Manufacturer: {port.manufacturer()}")
			print("-" * 20)

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
			print("Device was disconnected...")
			self.toggle_connection()
		elif error in [QSerialPort.SerialPortError.NotOpenError, QSerialPort.SerialPortError.NoError]:
			pass
		else:
			print(f"Error: {error}")
			self.toggle_connection()


if __name__ == "__main__":
	app = QApplication(sys.argv)
	window = MainWindow()
	window.show()
	sys.exit(app.exec())
