from __future__ import annotations

from typing import TYPE_CHECKING

from esptool.cmds import detect_chip, run, run_stub, write_flash

from . import BaseFlashingTool

if TYPE_CHECKING:
	from ..board_utils import BoardConfig

import contextlib


class ESP32(BaseFlashingTool):
	"""Flashing tool that programs ESP-IDF boards using esptool.

	Unlike the CLI-based tools, this drives the ``esptool`` Python API
	directly rather than spawning a subprocess.
	"""

	name = "esp32"

	def __init__(self, config_file: str = "") -> None:
		"""Initializes the tool, restricting it to ESP-IDF boards.

		Unlike :class:`CLIFlashingTool`, esptool has no CLI arguments to
		configure, so ``custom_settings`` (loaded by the base class along
		with ``name``, ``supported_file_types``, and the progress-bar
		settings) goes unused here.

		Args:
			config_file (str): Path to the tool's configuration TOML file.
				Defaults to ``""``.
		"""
		super().__init__(config_file)

		from ..board_utils import BoardType
		self.supported_board_types = [BoardType.ESPIDF]

	def flash(self, board: BoardConfig, port: str, file: str, settings: str = "default") -> bool:
		"""Detects the connected chip and flashes ``file`` onto it.

		Args:
			board (BoardConfig): The board being flashed.
			port (str): Serial port the board is connected to.
			file (str): Path to the firmware file to flash.
			settings (str): Unused by this tool; accepted for interface
				compatibility with :meth:`BaseFlashingTool.flash`, since
				esptool is driven directly rather than via configurable CLI
				args.
		"""
		super()
		self.step_on = 0
		self.p_bar.setValue(0)

		self.reset_console_format()

		try:
			with contextlib.redirect_stdout(self), contextlib.redirect_stderr(self), detect_chip(port=port) as esp:
				self.log_box.append(f"Chip Type: {esp.CHIP_NAME}")
				esp = run_stub(esp)

				write_flash(esp, [(0x10000, file)])

				run(esp)

		except Exception:
			self.logger.exception("Unknown exception")
			return False
		
		return True
