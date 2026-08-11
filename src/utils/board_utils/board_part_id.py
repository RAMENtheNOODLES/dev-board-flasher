from enum import Enum, unique
from ..custom_exceptions import UnknownPartID

@unique
class BoardPartID(Enum):
	"""Identifiers for microcontroller part numbers supported by boards."""

	UNDEF = 0
	ATMEGA328P = 1

def get_board_part_id(board_part_id: str) -> BoardPartID:
	"""Resolves a part ID string from a board config into a BoardPartID.

	Args:
		board_part_id (str): The part ID name as read from a board
			configuration file (case-insensitive).

	Returns:
		BoardPartID: The matching enum member.

	Raises:
		UnknownPartID: If ``board_part_id`` does not match any known
			:class:`BoardPartID` member.
	"""
	if (board_part_id.upper() in BoardPartID.__members__):
		return BoardPartID[board_part_id.upper()]
	else:
		raise UnknownPartID(board_part_id)