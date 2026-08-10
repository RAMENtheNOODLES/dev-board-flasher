from __future__ import annotations
from string import Template

import tomllib

from . import BaseFlashingTool

from typing import TYPE_CHECKING

if TYPE_CHECKING:
	from ..board_utils import BoardType, BoardConfig

import subprocess


class CLIFlashingTool(BaseFlashingTool):
	"""Flashing tool that runs an external CLI program defined by a config file.

	The CLI's arguments are read from ``tool_settings.args`` in the tool's
	TOML config and support ``$variable`` substitution (see
	:meth:`flash`), similar to PowerShell string expansion.
	"""

	def __init__(self, config_file: str) -> None:
		"""Loads a CLI flashing tool definition from a TOML config file.

		Args:
			config_file (str): Path to the tool's configuration TOML file.
		"""
		super().__init__()

		with open(config_file, "rb") as f:
			self.config_data = tomllib.load(f)

		self.name = self.config_data["tool_name"]
		self.supported_file_types: list[str] = self.config_data["tool_settings"]["supported_file_types"]

		boards: list[str] = self.config_data["tool_settings"]["supported_boards"]
		self.supported_board_types = []
		from ..board_utils.board_type import get_board_type
		for boardtype in boards:
			self.supported_board_types.append(get_board_type(boardtype))
			

	def flash(self, board: BoardConfig, port: str, file: str) -> None:
		"""Substitutes template variables into the configured args and runs the CLI.

		Supported substitution variables (referenced as ``$name`` in the
		tool's ``args`` config) are: ``partid``, ``port``, ``baudrate``,
		``boardname``, ``boardtype``, and ``file``.

		Args:
			board (BoardConfig): The board being flashed.
			port (str): Serial port the board is connected to.
			file (str): Path to the firmware file to flash.
		"""
		super()

		variables = {
			"partid": board.PartID.name,
			"port": port,
			"baudrate": str(board.BaudRate),
			"boardname": board.BoardName,
			"boardtype": board.Type.name,
			"file": file
		}

		parsedArgs: list[str] = []
		args: list[str] = self.config_data["tool_settings"]["args"]
		for arg in args:
			tpl = Template(arg)
			parsedArgs.append(tpl.substitute(variables))

		print(f"Unparsed arguments: {args}")
		print(f"Using these arguments for cli: {parsedArgs}")

		self.process.start(self.name, parsedArgs)

		