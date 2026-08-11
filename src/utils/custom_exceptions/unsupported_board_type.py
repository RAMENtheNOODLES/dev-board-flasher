from ..board_utils import BoardType
from ..flashing_tools import BaseFlashingTool

class UnsupportedBoardType(Exception):
	"""Raised when a flasher does not support a type of board.
	"""

	def __init__(self, board: BoardType, flashing_tool: BaseFlashingTool) -> None:
		"""Initializes the exception with a message describing the mismatch.

		Args:
			board (BoardType): The board type that was requested.
			flashing_tool (BaseFlashingTool): The flashing tool that does
				not support ``board``.
		"""
		super().__init__(f"Board ({board.name}) is unsupported by flashing tool ({flashing_tool.get_name()})...")