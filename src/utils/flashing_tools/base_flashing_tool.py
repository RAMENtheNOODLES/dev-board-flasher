from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from PySide6.QtCore import QProcess
from PySide6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QApplication, QProgressBar, QTextEdit

from ..wiz_utils import read_toml_file_from_url_or_path

if TYPE_CHECKING:
	from ..board_utils import BoardConfig, BoardType

# CSI Pm F per ECMA-48: parameter bytes 0x30-0x3F ("0"-"?", covering digits,
# ";", and the "?" DEC-private-mode marker used by sequences like win32-input-
# mode/focus-tracking that ConPTY-attached apps commonly emit), optional
# intermediate bytes 0x20-0x2F, then a single final byte 0x40-0x7E; or an OSC
# (Operating System Command) sequence -- e.g. ESC ] 0 ; <window title> BEL,
# commonly emitted by ConPTY-attached apps to set the console title/icon
# name -- terminated by BEL (0x07) or ST (ESC \\). group(1)/group(2) are
# unset for the OSC branch, so the "is this SGR" check below stays False.
_CSI_RE = re.compile(
	r"\x1b\[([0-?]*)[ -/]*([@-~])"
	r"|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)"
)

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
		name (str): Human-readable name of the flashing tool. Populated from
			``tool_name``.
		config_data (dict): Parsed contents of the tool's TOML config file.
		boards (list[str]): Raw board type names from
			``tool_settings.supported_boards``, resolved into
			``supported_board_types`` by subclasses.
		supported_board_types (list[BoardType]): Board types this tool can
			flash.
		supported_file_types (list[str]): Glob patterns of firmware file
			types this tool accepts.
		tool_loc (str): Path to the tool executable, or ``""`` to use the
			system PATH. Populated from ``tool_loc``.
		process (QProcess | ConPtyProcess): Process used to run the underlying
			flashing command. A plain ``QProcess`` by default; a
			:class:`ConPtyProcess` instead when ``use_pty`` is set, so tools
			that write via Win32 console APIs still produce captured output.
		use_pty (bool): Whether to run the tool attached to a pseudo console
			(see :class:`ConPtyProcess`) instead of a plain ``QProcess``.
			Populated from ``tool_settings.use_pty``; defaults to ``False``.
		stop_on (list[str]): Markers that, if seen in the process's output,
			cause the process to be killed. For tools that finish their real
			work but then hang on a prompt (e.g. "press enter to exit")
			rather than exiting on their own. Populated from
			``tool_settings.stop_on``; defaults to an empty list (never
			force-killed). See :meth:`read_terminal_stream`.
		log_box (QTextEdit): Text widget that flashing output is streamed
			to. Set via :meth:`set_log_box` before calling :meth:`flash`.
		custom_settings (dict[str, list[str]]): Named presets of tool-specific
			settings (e.g. ``default``, ``dry_run``), keyed by the name shown
			in the settings dropdown. Populated from ``tool_settings.custom_settings``
			by subclasses that support multiple presets. See :meth:`get_settings`.
		sub_settings (dict[str, dict[str, str]]): Named presets of extra
			``$variable`` values (e.g. per-board memory offsets), keyed by
			the name shown in the sub-settings dropdown; each preset is a
			table of ``variable name -> value`` pairs merged into the
			substitution variables available to ``custom_settings`` argument
			lists. Populated from
			``tool_settings.custom_settings.sub_settings``. See
			:meth:`get_sub_settings` and :meth:`CLIFlashingTool.flash`.
		p_bar (QProgressBar): Progress bar widget updated as the flashing
			process runs. Set via :meth:`set_progress_bar` before calling
			:meth:`flash`.
		num_steps (int): Number of steps the progress bar is divided into
			when ``step_method`` is ``"step_array"``. Populated from
			``tool_settings.progress_bar.num_steps``.
		step_read (str): Regex used to read the current step count out of
			process output when ``step_method`` is ``"regex"`` and
			``regex_method`` is ``"normal"``. Populated from
			``tool_settings.progress_bar.step_read_regex``.
		step_final (str): Regex used to read the total step count out of
			process output when ``step_method`` is ``"regex"`` and
			``regex_method`` is ``"normal"``. Populated from
			``tool_settings.progress_bar.step_final_regex``.
		step_method (str): How progress is derived from process output:
			``"none"``, ``"step_array"``, or ``"regex"``. Populated from
			``tool_settings.progress_bar.method``. See
			:meth:`update_progress_bar`.
		regex_method (str): Which ``"regex"`` sub-strategy to use:
			``"normal"`` reads current/total counts via ``step_read``/
			``step_final``, ``"hex"`` reads hex memory addresses via
			``initial_address``/``final_address``/``next_address`` instead.
			Populated from ``tool_settings.progress_bar.regex_method``.
		initial_address (str): ``regex_method == "hex"`` only. Regex matching
			the starting hex address of the flash range in process output.
			Populated from ``tool_settings.progress_bar.initial_address``.
		final_address (str): ``regex_method == "hex"`` only. Regex matching
			the ending hex address of the flash range in process output,
			used with ``initial_address`` to compute the bar's maximum.
			Populated from ``tool_settings.progress_bar.final_address``.
		next_address (str): ``regex_method == "hex"`` only. Regex matching
			the current hex address reached in process output, used with
			``initial_address`` to compute the bar's value. Populated from
			``tool_settings.progress_bar.next_address``.
		step_on (int): Index into ``progress_on`` of the marker currently
			being watched for, when ``step_method`` is ``"step_array"``.
		progress_on (list[str]): Ordered markers to watch for in process
			output when ``step_method`` is ``"step_array"``; each match
			advances the bar and moves on to the next marker, wrapping
			around at the end. Populated from
			``tool_settings.progress_bar.inc_step_on``.
	"""

	name = "Base"
	# Not mutable class defaults: __init__ always reassigns each of these
	# per-instance from the tool's config file, so the bare annotations here
	# just document the expected type without sharing one list/dict object
	# across instances before __init__ runs.
	supported_board_types: list[BoardType]
	supported_file_types: list[str]
	tool_loc: str = ""
	custom_settings: dict[str, list[str]]
	sub_settings: dict[str, dict[str, str]]
	num_steps = 0
	step_read = ""
	step_final = ""
	step_method = "none"
	step_on = 0
	progress_on: list[str]

	def __init__(self, config_file: str) -> None:
		"""Loads ``config_file`` and sets up the underlying process.

		Args:
			config_file (str): Local path or GitHub URL of the tool's
				configuration TOML file (see
				:func:`wiz_utils.read_toml_file_from_url_or_path`).
				Populates ``name``, ``supported_file_types``, ``boards``,
				``tool_loc``, ``custom_settings``, ``sub_settings``,
				``use_pty``, ``stop_on``, and the progress-bar settings
				described in the class docstring.

		Raises:
			RuntimeError: If ``config_file`` couldn't be read (e.g. a failed
				remote fetch).
		"""
		self.logger = logging.getLogger(__name__)

		self._ansi_format = QTextCharFormat()

		self.config_data = read_toml_file_from_url_or_path(config_file)
		if self.config_data is None:
			raise RuntimeError("Failed to read config data...")

		self.name = self.config_data["tool_name"]
		self.supported_file_types: list[str] = self.config_data["tool_settings"]["supported_file_types"]

		self.boards: list[str] = self.config_data["tool_settings"]["supported_boards"]
		self.supported_board_types = []
		self.tool_loc = self.config_data["tool_loc"]

		self.progress_on: list[str] = self.config_data["tool_settings"].get("progress_bar", {}).get("inc_step_on", ["#"])
		self.num_steps = self.config_data["tool_settings"].get("progress_bar", {}).get("num_steps", 50)
		self.step_read = self.config_data["tool_settings"].get("progress_bar", {}).get("step_read_regex", "")
		self.step_final = self.config_data["tool_settings"].get("progress_bar", {}).get("step_final_regex", "")
		self.step_method = self.config_data["tool_settings"].get("progress_bar", {}).get("method", "none")
		self.regex_method = self.config_data["tool_settings"].get("progress_bar", {}).get("regex_method", "")
		self.final_address = self.config_data["tool_settings"].get("progress_bar", {}).get("final_address", "")
		self.next_address = self.config_data["tool_settings"].get("progress_bar", {}).get("next_address", "")
		self.initial_address = self.config_data["tool_settings"].get("progress_bar", {}).get("initial_address", "")
		self.custom_settings = self.config_data["tool_settings"].get("custom_settings", {})
		self.sub_settings = self.config_data["tool_settings"].get("custom_settings", {}).get("sub_settings", {})
		self.use_pty: bool = self.config_data["tool_settings"].get("use_pty", False)
		self.stop_on: list[str] = self.config_data["tool_settings"].get("stop_on", [])

		# Progress bar regex variables
		self.final: int|None = None
		self.next_initial: int|None = None
		self.step_on = 0

		# 3. Process Setup
		if self.use_pty:
			# Some CLI tools write progress/status via Win32 console APIs
			# (WriteConsole, colored SetConsoleTextAttribute output) rather
			# than plain stdout writes. Those calls silently no-op against
			# QProcess's anonymous pipes, so such tools need a real console
			# handle via ConPTY to produce any captured output at all.
			from .conpty_process import ConPtyProcess
			self.process = ConPtyProcess()
		else:
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
		self.logger.info("Starting process...")

	def flash(self, board: BoardConfig, port: str, file: str, settings: str = "default", sub_settings: str = "default") -> bool:
		"""Flashes ``file`` onto ``board`` over ``port``.

		Subclasses must override this to start the actual flashing process.
		The base implementation only runs the shared preamble.

		Args:
			board (BoardConfig): The board being flashed.
			port (str): Serial port the board is connected to.
			file (str): Path to the firmware file to flash.
			settings (str): Name of the settings preset (a key of
				``custom_settings``) to flash with. Defaults to ``"default"``.
			sub_settings (str): Name of the sub-settings preset (a key of
				``sub_settings``) whose ``$variable`` values are merged in
				alongside ``settings``. Defaults to ``"default"``.
		"""
		self.flash_preamble()
		self.p_bar.setValue(0)

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

	def set_progress_bar(self, p_bar: QProgressBar) -> None:
		"""Sets the progress bar that flashing progress should be reported to.

		Args:
			p_bar (QProgressBar): The progress bar widget to update as the
				flashing process runs. Must be set before calling
				:meth:`flash`.
		"""
		self.p_bar = p_bar

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

		esptool-style progress bars print a lone ``\\r`` (not part of a
		``\\r\\n`` pair) to overwrite the current line, so a literal insert
		would flood the log with dozens of stale lines. This mimics
		terminal behavior by erasing back to the start of the current line
		whenever such a carriage return is seen. A ``\\r\\n`` pair -- an
		ordinary Windows line ending, e.g. from a ConPTY-attached process --
		is treated as a plain newline instead, so each new line doesn't
		erase the one before it.

		Args:
			cursor (QTextCursor): Cursor positioned in the log box where
				``chunk`` should be inserted.
			chunk (str): Text to insert, potentially containing ``\\r``
				line-overwrite characters but no CSI escape sequences.
		"""
		if not chunk:
			return

		chunk = chunk.replace("\r\n", "\n")
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
		self.logger.debug(f"Raw Text: {text}")
		if not text:
			return 0

		if self.step_method.lower() != "none":
			self.update_progress_bar(text)

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

	def update_progress_bar(self, data: str) -> None:
		"""Advances ``self.p_bar`` based on a chunk of process output.

		Interprets ``data`` according to ``self.step_method``, which is
		populated from a tool's ``tool_settings.progress_bar`` config:

		- ``"step_array"``: Each occurrence of ``self.progress_on[self.step_on]``
			found in ``data`` advances the bar by ``100 // self.num_steps``.
			After a match, ``self.step_on`` moves to the next entry in
			``self.progress_on``, wrapping back to the start once the list is
			exhausted.
		- ``"regex"``: Behavior depends on ``self.regex_method``:

			- ``"normal"``: ``self.step_read`` and ``self.step_final`` are
				matched against ``data`` to extract the current and total
				step counts (e.g. from ``"12/50"``-style output); when both
				match, the bar's maximum and value are set directly from
				them.
			- Any other value (treated as ``"hex"``): ``self.initial_address``,
				``self.final_address``, and ``self.next_address`` are matched
				against ``data`` to extract hex memory addresses. Once the
				initial and final addresses have both been seen, the bar's
				maximum is set to ``final - initial``; each subsequent match
				of ``self.next_address`` sets the bar's value to
				``next - initial``. Suits tools (e.g. esptool's hex-address
				write progress) that report progress as absolute flash
				addresses rather than a step count.
		- Any other value (e.g. ``"none"``): no-op.

		Args:
			data (str): A chunk of decoded process output to scan for
				progress markers.
		"""
		if (self.step_method.lower() == "step_array"):
			if (self.progress_on[self.step_on] in data):
				split = data.split(self.progress_on[self.step_on])

				self.logger.debug(f"Data: {data}")
				self.logger.debug(f"Split length: {len(split)}")

				for _ in range(len(split) - 1):
					self.p_bar.setValue(self.p_bar.value() + (100 // self.num_steps))
				
				self.step_on += 1

				if (self.step_on > len(self.progress_on) - 1):
					self.step_on = 0
		elif (self.step_method.lower() == "regex"):
			if self.regex_method == "normal":
				self.logger.info(f"Read Regex: {self.step_read}, Final Regex: {self.step_final}")
				current = re.search(self.step_read, data)
				out_of = re.search(self.step_final, data)

				if (current is not None and out_of is not None):
					self.p_bar.setMaximum(int(out_of.group()))
					self.p_bar.setValue(int(current.group()))
			else:
				next_final = re.search(self.final_address, data)
				next_initial = re.search(self.initial_address, data)

				if (next_initial is not None):
					self.next_initial = int(next_initial.group(), 16)

				if (next_final is not None and self.next_initial is not None):
					self.p_bar.setValue(0)
					self.final = int(next_final.group(), 16) - self.next_initial
					self.p_bar.setMaximum(self.final)
					self.logger.debug(f"New max pbar value: {self.final}")

				next_addr = re.search(self.next_address, data)

				if (self.final is not None and next_addr is not None and self.next_initial is not None):
					new_val = int(next_addr.group(), 16) - self.next_initial
					self.logger.debug(f"New pbar value: {new_val}")
					self.p_bar.setValue(new_val)

	def read_terminal_stream(self):
		"""Reads buffered process output and appends it to the log box.

		Routed through :meth:`write` (the same path ``ESP32`` drives via
		``redirect_stdout``) so CLI/ConPTY tool output gets the same ANSI
		SGR parsing and ``\\r`` line-overwrite handling, rather than
		dumping raw escape codes into the log box. Connected to the
		underlying process's ``readyReadStandardOutput`` signal.

		If this chunk contains one of ``self.stop_on``'s markers, the
		process is killed once written -- for tools that finish their real
		work but then sit on a prompt (e.g. "press enter to exit") instead
		of exiting on their own, which would otherwise hang the flash
		indefinitely.
		"""
		# Convert the memoryview object explicitly into bytes, then decode it
		raw_data = self.process.readAllStandardOutput().data()
		data = bytes(raw_data).decode(errors="ignore")

		self.write(data)

		if any(marker in data for marker in self.stop_on):
			self.logger.info("Stop-on marker matched in process output; killing process.")
			self.process.kill()

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
			self.logger.info("[PROCESS COMPLETED SUCCESSFULLY]")
		else:
			self.log_box.append(f"\n[PROCESS FAILED WITH EXIT CODE {exit_code}]")
			self.logger.error(f"[PROCESS FAILED WITH EXIT CODE {exit_code}]")

	def get_settings(self) -> list[str]:
		"""Returns the names of the available settings presets.

		Returns:
			list[str]: Keys of ``custom_settings``, suitable for populating
				the settings dropdown and passing as the ``settings``
				argument to :meth:`flash`.
		"""
		out = []

		for key in self.custom_settings:
			if key != "sub_settings":
				out.append(key)

		return list(out)

	def get_sub_settings(self) -> list[str]:
		"""Returns the names of the available sub-settings presets.

		Returns:
			list[str]: Keys of ``sub_settings``, suitable for populating the
				sub-settings dropdown and passing as the ``sub_settings``
				argument to :meth:`flash`.
		"""
		return list(self.sub_settings.keys())
	