import logging
from pathlib import Path

from ..custom_exceptions import UnknownFlasherType, UnsupportedBoardType
from ..flashing_tools import BaseFlashingTool, cli_flashing_tool, esp32
from ..wiz_utils import get_remote_configs, read_toml_file_from_url_or_path
from .board_type import BoardType


class FlasherFinder:
	"""Discovers and instantiates flashing tools from configuration files.

	Attributes:
		tools (dict[str, BaseFlashingTool]): Flashing tool instances keyed
			by their lowercased tool name.
	"""

	tools: dict[str, BaseFlashingTool]

	def __init__(self, ext_tools: list[str] | None = None, cache: dict[str, dict | None] | None = None) -> None:
		"""Discovers flashing tool configuration files and builds tool instances.

		Args:
			ext_tools (list[str] | None, optional): Local paths and/or
				GitHub URLs of extra flashing tool TOML files, loaded in
				addition to ``config/flashing_tools``. Defaults to ``None``
				(no extra tools).
			cache (dict[str, dict | None] | None, optional): Shared memo of
				already-resolved remote configs (see
				:func:`wiz_utils.read_toml_file_from_url_or_path`), so
				discovery and parsing don't each re-fetch the same URL.
				Defaults to ``None``.
		"""
		self.ext_tools = ext_tools if ext_tools is not None else []
		self.tools = self.parse_tools(self.get_tools(self.ext_tools, cache), cache)
		self.logger = logging.getLogger(__name__)

	@staticmethod
	def get_tools(ext_tools: list[str] | None = None, cache: dict[str, dict | None] | None = None) -> list[str]:
		"""Retrieves flashing tool configuration files from the config path, plus any remote ones.

		Args:
			ext_tools (list[str] | None, optional): Local paths and/or
				GitHub URLs to check for flashing tool configs, in addition
				to the bundled ``config/flashing_tools`` folder. Defaults to
				``None`` (no extra tools).
			cache (dict[str, dict | None] | None, optional): Shared memo
				passed through to :meth:`get_tool_configs`. Defaults to
				``None``.

		Returns:
			list[str]: Paths/URLs of all flashing tool TOML files found,
				from both ``config/flashing_tools`` and ``ext_tools``.
		"""
		ext_tools = ext_tools if ext_tools is not None else []
		logger = logging.getLogger(__name__)
		tool_confs: list[str] = FlasherFinder.get_tool_configs(ext_tools, cache)

		current_dir = Path(__file__).resolve().parent
		if "__compiled__" in globals():
			# Nuitka onefile build: the extraction root corresponds directly to
			# the "src" directory (no extra "src" nesting level like in source runs).
			config_path = current_dir.parent.parent / "config" / "flashing_tools"
		else:
			config_path = current_dir.parent.parent.parent / "config" / "flashing_tools"

		tool_confs.extend([str(f) for f in config_path.iterdir() if (f.is_file() and f.suffix == ".toml")])

		logger.debug(f"tool confs: {tool_confs}")

		return tool_confs

	@staticmethod
	def get_tool_configs(remote_configs: list[str], cache: dict[str, dict | None] | None = None) -> list[str]:
		"""Filters ``remote_configs`` down to the ones that declare a flashing tool.

		Args:
			remote_configs (list[str]): Local paths and/or GitHub URLs to
				check.
			cache (dict[str, dict | None] | None, optional): Shared memo
				passed through to :func:`wiz_utils.get_remote_configs`.
				Defaults to ``None``.

		Returns:
			list[str]: The subset of ``remote_configs`` whose parsed TOML
				contains a ``tool_name`` key.
		"""
		return get_remote_configs(remote_configs, "tool_name", cache)

	@staticmethod
	def parse_tools(tools: list[str], cache: dict[str, dict | None] | None = None) -> dict[str, BaseFlashingTool]:
		"""Parses flashing tool configuration files into tool instances.

		CLI-type tools are instantiated as :class:`CLIFlashingTool` from
		their config file. Python-type tools are matched by name to a
		built-in implementation (currently only ``esp32``).

		Args:
			tools (list[str]): Paths/URLs to flashing tool configuration
				TOML files, as returned by :meth:`get_tools`.
			cache (dict[str, dict | None] | None, optional): Shared memo of
				already-resolved remote configs, passed through to
				:func:`wiz_utils.read_toml_file_from_url_or_path`. Defaults
				to ``None``.

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
			config_data = read_toml_file_from_url_or_path(tool, cache)

			if config_data is None:
				continue
			
			tool_type = config_data["tool_settings"]["type"].lower()
			if (tool_type == "cli"):
				out[config_data["tool_name"].lower()] = cli_flashing_tool.CLIFlashingTool(tool)
			elif (tool_type == "python"):
				name: str = config_data["tool_name"].lower()

				match name:
					case "esp32":
						out[name] = esp32.ESP32(tool)
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