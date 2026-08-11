from __future__ import annotations

from typing import NamedTuple, TYPE_CHECKING

if TYPE_CHECKING:
	from ..flashing_tools import BaseFlashingTool
	from . import BoardType, BoardPartID


class BoardConfig(NamedTuple):
	"""Resolved configuration for a single dev board.

	Produced by :meth:`BoardConfigurer.read_board_config` from a board's
	TOML configuration file.

	Attributes:
		BoardName (str): Human-readable name of the board.
		Flasher (BaseFlashingTool): Flashing tool used to program the board.
		BaudRate (int): Baud rate used for flashing and serial communication.
		PartID (BoardPartID): Identifier of the board's microcontroller part.
		Type (BoardType): The board's toolchain/platform type.
		SupportedFiles (list[str]): Glob patterns of firmware file types the
			board's flashing tool accepts.
	"""

	BoardName: str
	Flasher: BaseFlashingTool
	BaudRate: int
	PartID: BoardPartID
	Type: BoardType
	SupportedFiles: list[str]

