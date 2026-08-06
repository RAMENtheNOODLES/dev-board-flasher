from __future__ import annotations

from typing import NamedTuple, TYPE_CHECKING

if TYPE_CHECKING:
	from ..flashing_tools import BaseFlashingTool
	from . import BoardType, BoardPartID


class BoardConfig(NamedTuple):
	BoardName: str
	Flasher: BaseFlashingTool
	BaudRate: int
	PartID: BoardPartID
	Type: BoardType
	SupportedFiles: list[str]

