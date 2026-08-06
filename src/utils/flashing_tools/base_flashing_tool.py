from __future__ import annotations

from PySide6.QtCore import QProcess
from PySide6.QtWidgets import QTextEdit

from typing import TYPE_CHECKING

if TYPE_CHECKING:
	from ..board_utils import BoardType, BoardConfig

class BaseFlashingTool:
	name = "Base"
	supported_board_types: list[BoardType] = []
	supported_file_types: list[str] = []

	def __init__(self) -> None:
		# 3. Process Setup
		self.process = QProcess()
		
		# Merge standard output and standard error into a single stream
		self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
		
		# Connect process signals to our custom UI methods
		self.process.readyReadStandardOutput.connect(self.read_terminal_stream)
		self.process.finished.connect(self.process_finished)

	def flash_preamble(self):
		self.log_box.clear()
		self.log_box.append("Starting process...\n")

	def flash(self, board: BoardConfig, port: str, file: str) -> None:
		self.flash_preamble()

	def get_supported_boards(self):
		return self.supported_board_types

	def get_name(self):
		return self.name

	def get_supported_file_types(self):
		return self.supported_file_types

	def set_log_box(self, log_box: QTextEdit):
		self.log_box: QTextEdit = log_box

	def read_terminal_stream(self):
		# Convert the memoryview object explicitly into bytes, then decode it
		raw_data = self.process.readAllStandardOutput().data()
		data = bytes(raw_data).decode(errors="ignore")
		
		# Insert the text chunk and automatically snap the scrollbar to the bottom
		self.log_box.insertPlainText(data)
		self.log_box.ensureCursorVisible()

	def process_finished(self, exit_code, exit_status):
		if exit_code == 0:
			self.log_box.append("\n[PROCESS COMPLETED SUCCESSFULLY]")
		else:
			self.log_box.append(f"\n[PROCESS FAILED WITH EXIT CODE {exit_code}]")

	
	