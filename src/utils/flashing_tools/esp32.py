from __future__ import annotations

from . import BaseFlashingTool

import esptool
import tomllib

from esptool.cmds import detect_chip, run_stub, write_flash, run

from typing import TYPE_CHECKING

if TYPE_CHECKING:
	from ..board_utils import BoardType, BoardConfig

import contextlib


class ESP32(BaseFlashingTool):
	"""Flashing tool that programs ESP-IDF boards using esptool.

	Unlike the CLI-based tools, this drives the ``esptool`` Python API
	directly rather than spawning a subprocess.
	"""

	name = "esp32"
	supported_file_types: list[str] = ["*.hex", "*.bin"]

	def __init__(self, config_file: str = "") -> None:
		"""Initializes the tool, restricting it to ESP-IDF boards.

		Unlike :class:`CLIFlashingTool`, esptool has no CLI arguments to
		configure, so ``config_file`` is only read for its
		``tool_settings.progress_bar`` table.

		Args:
			config_file (str): Path to the tool's configuration TOML file,
				used to populate progress-bar settings (``method``,
				``num_steps``, ``inc_step_on``, ``step_read_regex``,
				``step_final_regex``). Defaults to ``""``.
		"""
		super().__init__()

		with open(config_file, "rb") as f:
			self.config_data = tomllib.load(f)

		from ..board_utils import BoardType, BoardConfig
		self.supported_board_types = [BoardType.ESPIDF]
		self.progress_on: list[str] = self.config_data["tool_settings"].get("progress_bar", {}).get("inc_step_on", ["#"])
		self.num_steps = self.config_data["tool_settings"].get("progress_bar", {}).get("num_steps", 50)
		self.step_read = self.config_data["tool_settings"].get("progress_bar", {}).get("step_read_regex", "")
		self.step_final = self.config_data["tool_settings"].get("progress_bar", {}).get("step_final_regex", "")
		self.step_method = self.config_data["tool_settings"].get("progress_bar", {}).get("method", "none")
		self.step_on = 0

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
			with contextlib.redirect_stdout(self), contextlib.redirect_stderr(self):
				with detect_chip(port=port) as esp:
					self.log_box.append(f"Chip Type: {esp.CHIP_NAME}")
					esp = run_stub(esp)

					write_flash(esp, [(int(0x10000), file)])

					run(esp)

		except Exception as e:
			self.logger.exception("Unknown exception")
			return False
		
		return True
