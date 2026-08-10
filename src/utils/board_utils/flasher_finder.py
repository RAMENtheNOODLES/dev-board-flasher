import tomllib
from pathlib import Path

from ..flashing_tools import BaseFlashingTool, cli_flashing_tool, esp32
from ..custom_exceptions import UnknownFlasherType, UnsupportedBoardType
from .board_type import BoardType

class FlasherFinder:
	"""Discovers and instantiates flashing tools from configuration files.

	Attributes:
		tools (dict[str, BaseFlashingTool]): Flashing tool instances keyed
			by their lowercased tool name.
	"""

	tools: dict[str, BaseFlashingTool]

	def __init__(self) -> None:
		"""Discovers flashing tool configuration files and builds tool instances."""
		self.tools = self.parse_tools(self.get_tools())

	@staticmethod
	def get_tools() -> list[str]:
		"""Retrieves flashing tool configuration files from the config path.

		Returns:
			list[str]: Paths to all TOML files found in the
				``config/flashing_tools`` folder.
		"""
		current_dir = Path(__file__).resolve().parent
		config_path = current_dir.parent.parent.parent / "Config" / "flashing_tools"

		tool_confs: list[str] = [str(f) for f in config_path.iterdir() if (f.is_file() and f.suffix == ".toml")]

		print(f"tool confs: {tool_confs}")

		return tool_confs

	@staticmethod
	def parse_tools(tools: list[str]) -> dict[str, BaseFlashingTool]:
		"""Parses flashing tool configuration files into tool instances.

		CLI-type tools are instantiated as :class:`CLIFlashingTool` from
		their config file. Python-type tools are matched by name to a
		built-in implementation (currently only ``esp32``).

		Args:
			tools (list[str]): Paths to flashing tool configuration TOML
				files, as returned by :meth:`get_tools`.

		Returns:
			dict[str, BaseFlashingTool]: Flashing tool instances keyed by
				their lowercased tool name.

		Raises:
			UnknownFlasherType: If a config declares an unsupported
				``tool_settings.type``, or a ``python``-type tool whose name
				has no built-in implementation.
		"""
		out: dict[str, BaseFlashingTool] = {}
		for tool in tools:
			with open(tool, "rb") as f:
				config_data = tomllib.load(f)
			tool_type = config_data["tool_settings"]["type"].lower()
			if (tool_type == "cli"):
				out[config_data["tool_name"].lower()] = cli_flashing_tool.CLIFlashingTool(tool)
			elif (tool_type == "python"):
				name: str = config_data["tool_name"].lower()

				match name:
					case "esp32":
						out[name] = esp32.ESP32()
					case _:
						raise UnknownFlasherType(name)
			else:
				raise UnknownFlasherType(tool_type)

		return out

	def get_flashing_tool(self, flasher_name: str, board_type: BoardType) -> BaseFlashingTool:
		"""Looks up a flashing tool by name and validates board type support.

		Args:
			flasher_name (str): Name of the flashing tool, as declared in a
				board's ``board_settings.flasher`` value.
			board_type (BoardType): The board type the tool must support.

		Returns:
			BaseFlashingTool: The matching flashing tool instance.

		Raises:
			UnknownFlasherType: If no tool with ``flasher_name`` was
				discovered.
			UnsupportedBoardType: If the tool does not support
				``board_type``.
		"""
		try:
			out = self.tools[flasher_name]

			if (board_type in out.get_supported_boards()):
				return out
			else:
				raise UnsupportedBoardType(board_type, out)
		except KeyError:
			raise UnknownFlasherType(flasher_name)