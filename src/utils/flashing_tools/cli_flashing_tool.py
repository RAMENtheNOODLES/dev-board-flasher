from __future__ import annotations

from string import Template
from typing import TYPE_CHECKING

from . import BaseFlashingTool

if TYPE_CHECKING:
	from ..board_utils import BoardConfig



class CLIFlashingTool(BaseFlashingTool):
	"""Flashing tool that runs an external CLI program defined by a config file.

	The CLI's arguments are read from ``tool_settings.custom_settings`` in the
	tool's TOML config, a table of one or more named argument-list presets
	(e.g. ``default``, ``dry_run``) selectable at flash time via the
	``settings`` argument to :meth:`flash`. Each preset's arguments support
	``$variable`` substitution (see :meth:`flash`), similar to PowerShell
	string expansion.

	``tool_settings.custom_settings.sub_settings`` is a further table of
	named presets selectable via :meth:`flash`'s ``sub_settings`` argument,
	each mapping extra variable names to values (e.g. per-board memory
	offsets) that get merged into the substitution variables available to
	the ``custom_settings`` argument list above -- for tools whose
	arguments vary by target/board in ways a single fixed preset can't
	express. See ``config/example_flashing_tool.toml``.
	"""

	def __init__(self, config_file: str) -> None:
		"""Loads a CLI flashing tool definition from a TOML config file.

		Args:
			config_file (str): Path to the tool's configuration TOML file.
		"""
		super().__init__(config_file)

		

		from ..board_utils.board_type import get_board_type
		for boardtype in self.boards:
			self.supported_board_types.append(get_board_type(boardtype))
			

	def flash(self, board: BoardConfig, port: str, file: str, settings: str = "default", sub_settings: str = "default") -> bool:
		"""Substitutes template variables into the configured args and runs the CLI.

		Supported substitution variables (referenced as ``$name`` in the
		tool's ``custom_settings`` config) are: ``partid``, ``port``,
		``baudrate``, ``boardname``, ``boardtype``, and ``file``.

		Args:
			board (BoardConfig): The board being flashed.
			port (str): Serial port the board is connected to.
			file (str): Path to the firmware file to flash.
			settings (str): Name of the ``custom_settings`` preset whose
				argument list should be used. Defaults to ``"default"``; if
				the name isn't found, the CLI is run with no arguments.
			sub_settings (str): Name of the ``custom_settings.sub_settings``
				preset whose extra variable values should be merged in
				alongside the substitution variables listed above. Defaults
				to ``"default"``; if the name isn't found, no extra
				variables are added.
		"""
		super()

		self.step_on = 0
		self.p_bar.setValue(0)
		self.reset_console_format()

		self.logger.info(f"Progress bar mode: {self.step_method}")

		variables = {
			"partid": board.PartID.name,
			"port": port,
			"baudrate": str(board.BaudRate),
			"boardname": board.BoardName,
			"boardtype": board.Type.name,
			"file": file
		}

		current_sub_settings = self.sub_settings.get(sub_settings, {})

		for setting in current_sub_settings:
			variables[setting] = current_sub_settings[setting]

		parsedArgs: list[str] = []
		args: list[str] = self.custom_settings.get(settings, [])
		for arg in args:
			tpl = Template(arg)
			parsedArgs.append(tpl.substitute(variables))

		self.logger.debug(f"Unparsed arguments: {args}")
		self.logger.debug(f"Using these arguments for cli: {parsedArgs}")

		tool = self.tool_loc if (self.tool_loc != "") else self.name
		self.logger.info(f"Starting CLI tool: {tool}")
		self.process.start(self.tool_loc if (self.tool_loc != "") else self.name, parsedArgs)

		return True