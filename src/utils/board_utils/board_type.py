from enum import Enum, unique

@unique
class BoardType(Enum):
	"""Toolchain/platform categories that a board can belong to."""

	UNKNOWN = 0
	ARDUINO = 1
	ESPIDF = 2
	CUSTOM = 3


def get_board_type(board_type: str) -> BoardType:
	"""Resolves a board type string from a board config into a BoardType.

	Args:
		board_type (str): The board type name as read from a board
			configuration file (case-insensitive).

	Returns:
		BoardType: The matching enum member, or ``BoardType.UNKNOWN`` if
			``board_type`` does not match any known member.
	"""

	if (board_type.upper() in BoardType.__members__):
		return BoardType[board_type.upper()]
	else:
		return BoardType.UNKNOWN
