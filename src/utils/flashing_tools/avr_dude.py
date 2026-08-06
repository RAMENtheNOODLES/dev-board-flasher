from __future__ import annotations

from . import BaseFlashingTool

from typing import TYPE_CHECKING

if TYPE_CHECKING:
	from ..board_utils import BoardType, BoardConfig

import subprocess


class AVRDude(BaseFlashingTool):
	name = "avrdude"
	supported_file_types: list[str] = ["*.hex", "*.bin"]

	def __init__(self) -> None:
		super().__init__()

		from ..board_utils import BoardType, BoardConfig
		self.supported_board_types = [BoardType.ARDUINO]

	def flash(self, board: BoardConfig, port: str, file: str) -> None:
		super()

		args = [
			"-c", "arduino",
			"-p", board.PartID.name,
			"-P", port,
			"-b", str(board.BaudRate),
			"-D",
			"-U", f"flash:w:{file}:i"
		]

		self.process.start("avrdude", args)

		