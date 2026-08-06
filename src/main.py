import sys
from PySide6.QtCore import QIODevice, QTextStream, QEvent
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QFileDialog
from PySide6.QtSerialPort import QSerialPortInfo, QSerialPort
from PySide6.QtGui import QDragEnterEvent, QDragLeaveEvent, QDropEvent

from utils.board_utils import BoardConfigurer

# Import the auto-generated UI classes created by the Makefile
from ui_main_window import Ui_MainWindow


class MainWindow(QMainWindow, Ui_MainWindow):
	def __init__(self):
		super().__init__()
		self.setupUi(self) # Binds the primary main window layout

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

	def update_selected_board(self):
		self.selected_board = self.configurer.get_board_cache()[self.boardSelect.currentIndex()]

	def eventFilter(self, watched, event):
		# When the window scales, resize the overlay to fill the screen
		if event.type() == QEvent.Type.Resize:
			self.vignette.resize(self.size())
			self.vignette.move(0, 0)
			self.actualWidget.resize(self.centralWidget().size())
		return super().eventFilter(watched, event)

	def dragEnterEvent(self, event: QDragEnterEvent):
		if event.mimeData().hasUrls():
			event.acceptProposedAction()
			self.vignette.show()

	def dragLeaveEvent(self, event: QDragLeaveEvent):
		self.vignette.hide()

	def dropEvent(self, event: QDropEvent):
		self.vignette.hide()
		if event.mimeData().hasUrls():
			files = [url.toLocalFile() for url in event.mimeData().urls()]
			print("Dropped files:", files)
			# Update any labels or fields you designed here
			self.file_name = files[0]

			self.fileName.setText(self.file_name)

	def browse_files(self):
		self.file_name, _ = QFileDialog.getOpenFileName(
			self,
			"Open File",
			"",
			"Binary Files (*.bin *.hex);; All Files (*)"
		)

		if self.file_name:
			self.fileName.setText(self.file_name)

			print(f"File ready for upload: {self.file_name}")

	def upload_to_board(self):
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
		ports = QSerialPortInfo.availablePorts()

		self.serialPortsBox.clear()
		
		for port in ports:
			self.serialPortsBox.addItem(port.portName())
			print(f"Port Name: {port.portName()}")
			print(f"Description: {port.description()}")
			print(f"Manufacturer: {port.manufacturer()}")
			print("-" * 20)

	def handle_serial_error(self, error: QSerialPort.SerialPortError):
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
