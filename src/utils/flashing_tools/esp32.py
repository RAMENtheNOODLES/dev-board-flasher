from __future__ import annotations

from . import BaseFlashingTool

import esptool

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

	def __init__(self) -> None:
		"""Initializes the tool, restricting it to ESP-IDF boards."""
		super().__init__()

		from ..board_utils import BoardType, BoardConfig
		self.supported_board_types = [BoardType.ESPIDF]

	def flash(self, board: BoardConfig, port: str, file: str) -> bool:
		"""Detects the connected chip and flashes ``file`` onto it.

		Args:
			board (BoardConfig): The board being flashed.
			port (str): Serial port the board is connected to.
			file (str): Path to the firmware file to flash.
		"""
		super()

		self.reset_console_format()

		try:
			with contextlib.redirect_stdout(self), contextlib.redirect_stderr(self):
				with detect_chip(port=port) as esp:
					self.log_box.append(f"Chip Type: {esp.CHIP_NAME}")
					esp = run_stub(esp)

					write_flash(esp, [(int(0x10000), file)])

					run(esp)

		except:
			return False
		
		return True
