from ..board_utils import BoardType
from ..flashing_tools import BaseFlashingTool

class UnsupportedBoardType(Exception):
	"""Raised when a flasher does not support a type of board
	"""

	def __init__(self, board: BoardType, flashing_tool: BaseFlashingTool) -> None:
		super().__init__(f"Board ({board.name}) is unsupported by flashing tool ({flashing_tool.get_name()})...")