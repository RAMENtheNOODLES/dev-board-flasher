from __future__ import annotations

from PySide6.QtCore import QProcess
from PySide6.QtWidgets import QTextEdit

from typing import TYPE_CHECKING

if TYPE_CHECKING:
	from ..board_utils import BoardType, BoardConfig

class BaseFlashingTool:
	"""Base class for tools that flash firmware onto a board.

	Subclasses drive an external process (or override :meth:`flash`
	entirely) to program a board, streaming its output into a shared log
	box. Subclasses are expected to set ``name``, ``supported_board_types``,
	and ``supported_file_types``.

	Attributes:
		name (str): Human-readable name of the flashing tool.
		supported_board_types (list[BoardType]): Board types this tool can
			flash.
		supported_file_types (list[str]): Glob patterns of firmware file
			types this tool accepts.
		process (QProcess): Process used to run the underlying flashing
			command.
		log_box (QTextEdit): Text widget that flashing output is streamed
			to. Set via :meth:`set_log_box` before calling :meth:`flash`.
	"""

	name = "Base"
	supported_board_types: list[BoardType] = []
	supported_file_types: list[str] = []

	def __init__(self) -> None:
		"""Sets up the underlying QProcess and connects its signals."""
		# 3. Process Setup
		self.process = QProcess()
		
		# Merge standard output and standard error into a single stream
		self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
		
		# Connect process signals to our custom UI methods
		self.process.readyReadStandardOutput.connect(self.read_terminal_stream)
		self.process.finished.connect(self.process_finished)

	def flash_preamble(self):
		"""Clears the log box and writes a starting message.

		Called at the beginning of :meth:`flash` implementations.
		"""
		self.log_box.clear()
		self.log_box.append("Starting process...\n")

	def flash(self, board: BoardConfig, port: str, file: str) -> None:
		"""Flashes ``file`` onto ``board`` over ``port``.

		Subclasses must override this to start the actual flashing process.
		The base implementation only runs the shared preamble.

		Args:
			board (BoardConfig): The board being flashed.
			port (str): Serial port the board is connected to.
			file (str): Path to the firmware file to flash.
		"""
		self.flash_preamble()

	def get_supported_boards(self):
		"""Returns the board types this tool supports.

		Returns:
			list[BoardType]: The supported board types.
		"""
		return self.supported_board_types

	def get_name(self):
		"""Returns the human-readable name of this flashing tool.

		Returns:
			str: The tool's name.
		"""
		return self.name

	def get_supported_file_types(self):
		"""Returns the firmware file types this tool accepts.

		Returns:
			list[str]: Glob patterns of supported file types.
		"""
		return self.supported_file_types

	def set_log_box(self, log_box: QTextEdit):
		"""Sets the text widget that process output should be streamed to.

		Args:
			log_box (QTextEdit): The text widget to write log output to.
		"""
		self.log_box: QTextEdit = log_box

	def read_terminal_stream(self):
		"""Reads buffered process output and appends it to the log box.

		Connected to the underlying process's ``readyReadStandardOutput``
		signal.
		"""
		# Convert the memoryview object explicitly into bytes, then decode it
		raw_data = self.process.readAllStandardOutput().data()
		data = bytes(raw_data).decode(errors="ignore")

		# Insert the text chunk and automatically snap the scrollbar to the bottom
		self.log_box.insertPlainText(data)
		self.log_box.ensureCursorVisible()

	def process_finished(self, exit_code, exit_status):
		"""Appends a success or failure message once the process exits.

		Connected to the underlying process's ``finished`` signal.

		Args:
			exit_code (int): The process's exit code.
			exit_status (QProcess.ExitStatus): Whether the process exited
				normally or crashed.
		"""
		if exit_code == 0:
			self.log_box.append("\n[PROCESS COMPLETED SUCCESSFULLY]")
		else:
			self.log_box.append(f"\n[PROCESS FAILED WITH EXIT CODE {exit_code}]")

	
	