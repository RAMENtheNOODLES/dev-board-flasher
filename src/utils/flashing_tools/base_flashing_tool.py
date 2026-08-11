from __future__ import annotations

import re

from PySide6.QtCore import QProcess
from PySide6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QApplication, QTextEdit

from typing import TYPE_CHECKING

if TYPE_CHECKING:
	from ..board_utils import BoardType, BoardConfig

_CSI_RE = re.compile(r"\x1b\[([0-9;]*)([a-zA-Z])")

# Standard ANSI 16-color palette (SGR codes 30-37 normal, 90-97 bright).
_ANSI_COLORS = {
	30: "#000000", 31: "#cd3131", 32: "#0dbc79", 33: "#e5e510",
	34: "#2472c8", 35: "#bc3fbc", 36: "#11a8cd", 37: "#e5e5e5",
	90: "#666666", 91: "#f14c4c", 92: "#23d18b", 93: "#f5f543",
	94: "#3b8eea", 95: "#d670d6", 96: "#29b8db", 97: "#e5e5e5",
}


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
		custom_settings (dict[str, list[str]]): Named presets of tool-specific
			settings (e.g. ``default``, ``dry_run``), keyed by the name shown
			in the settings dropdown. Populated from ``tool_settings.custom_settings``
			by subclasses that support multiple presets. See :meth:`get_settings`.
	"""

	name = "Base"
	supported_board_types: list[BoardType] = []
	supported_file_types: list[str] = []
	tool_loc: str = ""
	custom_settings: dict[str, list[str]] = {}

	def __init__(self) -> None:
		"""Sets up the underlying QProcess and connects its signals."""
		# 3. Process Setup
		self.process = QProcess()
		
		# Merge standard output and standard error into a single stream
		self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
		
		# Connect process signals to our custom UI methods
		self.process.readyReadStandardOutput.connect(self.read_terminal_stream)
		self.process.finished.connect(self.process_finished)

		self._ansi_format = QTextCharFormat()

	def flash_preamble(self):
		"""Clears the log box and writes a starting message.

		Called at the beginning of :meth:`flash` implementations.
		"""
		self.log_box.clear()
		self.log_box.append("Starting process...\n")

	def flash(self, board: BoardConfig, port: str, file: str, settings: str = "default") -> bool:
		"""Flashes ``file`` onto ``board`` over ``port``.

		Subclasses must override this to start the actual flashing process.
		The base implementation only runs the shared preamble.

		Args:
			board (BoardConfig): The board being flashed.
			port (str): Serial port the board is connected to.
			file (str): Path to the firmware file to flash.
			settings (str): Name of the settings preset (a key of
				``custom_settings``) to flash with. Defaults to ``"default"``.
		"""
		self.flash_preamble()

		return False

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

	def reset_console_format(self) -> None:
		"""Clears any ANSI styling carried over from a previous write.

		Subclasses that stream a fresh run's output through :meth:`write`
		should call this beforehand, so leftover color/bold state from a
		prior run doesn't bleed into the new one.
		"""
		self._ansi_format = QTextCharFormat()

	def _apply_sgr(self, params: str) -> None:
		"""Updates ``self._ansi_format`` per an ANSI SGR escape's parameters.

		Args:
			params (str): The semicolon-separated numeric parameters of an
				SGR escape sequence (the text between ``\\x1b[`` and the
				trailing ``m``), e.g. ``"1;32"``.
		"""
		codes = [int(p) for p in params.split(";") if p] or [0]
		for code in codes:
			if code == 0:
				self._ansi_format = QTextCharFormat()
			elif code == 1:
				self._ansi_format.setFontWeight(QFont.Weight.Bold)
			elif code == 22:
				self._ansi_format.setFontWeight(QFont.Weight.Normal)
			elif code == 39:
				self._ansi_format.clearForeground()
			elif code == 49:
				self._ansi_format.clearBackground()
			elif code in _ANSI_COLORS:
				self._ansi_format.setForeground(QColor(_ANSI_COLORS[code]))
			elif 40 <= code <= 47 or 100 <= code <= 107:
				self._ansi_format.setBackground(QColor(_ANSI_COLORS[code - 10]))

	def _insert_with_cr(self, cursor: QTextCursor, chunk: str) -> None:
		"""Inserts ``chunk`` at ``cursor``, honoring ``\\r`` line-overwrites.

		esptool-style progress bars print ``\\r`` to overwrite the current
		line, so a literal insert would flood the log with dozens of stale
		lines. This mimics terminal behavior by erasing back to the start
		of the current line whenever a carriage return is seen.

		Args:
			cursor (QTextCursor): Cursor positioned in the log box where
				``chunk`` should be inserted.
			chunk (str): Text to insert, potentially containing ``\\r``
				line-overwrite characters but no CSI escape sequences.
		"""
		if not chunk:
			return

		for i, part in enumerate(chunk.split("\r")):
			if i > 0:
				cursor.movePosition(QTextCursor.MoveOperation.StartOfLine, QTextCursor.MoveMode.KeepAnchor)
				cursor.removeSelectedText()
			cursor.insertText(part, self._ansi_format)

	def write(self, text: str) -> int:
		"""Streams ``text`` into the log box in real time, parsing ANSI codes.

		This gives :class:`BaseFlashingTool` (and its subclasses) a
		file-like ``write``/``flush`` interface, so tools that drive a
		library directly (rather than an external process) can redirect
		``sys.stdout``/``sys.stderr`` straight to ``self`` via
		``contextlib.redirect_stdout``/``redirect_stderr``. ANSI SGR escape
		codes (color, bold, etc.) are translated into ``QTextCharFormat``
		styling instead of being printed literally; other CSI escape
		sequences (cursor movement, etc.) are dropped since the log box has
		no terminal to interpret them.

		Args:
			text (str): The text to append to the log box.

		Returns:
			int: The number of characters written, matching the file-like
				``write`` protocol.
		"""
		if not text:
			return 0

		cursor = self.log_box.textCursor()
		cursor.movePosition(QTextCursor.MoveOperation.End)

		pos = 0
		for match in _CSI_RE.finditer(text):
			self._insert_with_cr(cursor, text[pos:match.start()])
			if match.group(2) == "m":
				self._apply_sgr(match.group(1))
			pos = match.end()
		self._insert_with_cr(cursor, text[pos:])

		self.log_box.setTextCursor(cursor)
		self.log_box.ensureCursorVisible()

		# Flashing runs synchronously on the GUI thread, so nudge the event
		# loop to repaint instead of only showing output at the end.
		QApplication.processEvents()

		return len(text)

	def flush(self) -> None:
		"""No-op flush to satisfy the file-like ``write``/``flush`` protocol.

		:meth:`write` renders text into the log box immediately, so there is
		no buffered data to flush.
		"""
		pass

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

	def get_settings(self) -> list[str]:
		"""Returns the names of the available settings presets.

		Returns:
			list[str]: Keys of ``custom_settings``, suitable for populating
				the settings dropdown and passing as the ``settings``
				argument to :meth:`flash`.
		"""
		return list(self.custom_settings.keys())

	
	