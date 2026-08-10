import tomllib
from pathlib import Path

from .board_config import BoardConfig
from .board_type import get_board_type
from .board_part_id import get_board_part_id

# Import all flashing tool variants
from .flasher_finder import FlasherFinder


class BoardConfigurer:
	"""Finds and configures boards automatically
	"""

	_board_cache: list[BoardConfig|None] = []

	def __init__(self, ext_tool_path: str = "", ext_board_path: str = ""):
		"""Initializes the configurer and builds the initial board cache."""
		self.ext_tool_path = ext_tool_path if (ext_tool_path != "") else ""
		self.ext_board_path = ext_board_path if (ext_board_path != "") else None
		self.refresh_cache()

	def refresh_cache(self):
		"""Rebuilds the board cache from the board configuration files on disk."""
		boards = self.get_boards(self.ext_board_path)
		self._board_cache = [self.read_board_config(board, self.ext_tool_path) for board in boards]

	def get_board_cache(self) -> list[BoardConfig|None]:
		"""Returns the cached list of parsed board configurations.

		Returns:
			list[BoardConfig]: The board configurations loaded from
				``config/boards``.
		"""
		return self._board_cache

	@staticmethod
	def get_boards(ext_path: str|None = None) -> list[str]:
		"""Retrieves board configuration files from the config path

		Returns:
			list[str]: A list of all files found in the config/boards folder
		"""

		board_confs: list[str] = []

		if (ext_path is not None):
			ext_dir = Path(ext_path).resolve()
			print(f"get_boards(), Ext dir: {ext_dir}")
			board_confs = [str(f) for f in ext_dir.iterdir() if (f.is_file() and f.suffix == ".toml")]

		current_dir = Path(__file__).resolve().parent
		if "__compiled__" in globals():
			# Nuitka onefile build: the extraction root corresponds directly to
			# the "src" directory (no extra "src" nesting level like in source runs).
			config_path = current_dir.parent.parent / "config" / "boards"
		else:
			config_path = current_dir.parent.parent.parent / "config" / "boards"

		board_confs.extend([str(f) for f in config_path.iterdir() if (f.is_file() and f.suffix == ".toml")])

		return board_confs

	@staticmethod
	def read_board_config(conf_file: str, ext_tools: str = "") -> BoardConfig|None:
		"""Parses a single board configuration TOML file into a BoardConfig.

		Resolves the board's part ID, board type, and flashing tool
		(via :class:`FlasherFinder`) from the values declared in the file.

		Args:
			conf_file (str): Path to the board configuration TOML file.

		Returns:
			BoardConfig: The fully resolved configuration for the board.

		Raises:
			UnknownPartID: If ``board_settings.part_id`` is not a known
				:class:`BoardPartID`.
			UnknownFlasherType: If ``board_settings.flasher`` does not match
				a discovered flashing tool.
			UnsupportedBoardType: If the resolved flashing tool does not
				support the board's type.
		"""
		try:
			with open(conf_file, "rb") as f:
				config_data = tomllib.load(f)
		except FileNotFoundError:
			return None

		print(f"Got config data: {config_data}")

		board_name = config_data["board_name"]

		part_id = get_board_part_id(config_data["board_settings"]["part_id"])

		board_type = get_board_type(config_data["board_settings"]["type"])

		ff = FlasherFinder(ext_tools)

		flashing_tool = ff.get_flashing_tool(config_data["board_settings"]["flasher"], board_type)

		baud_rate = config_data["board_settings"]["baud_rate"]

		return BoardConfig(board_name, flashing_tool, baud_rate, part_id, board_type, flashing_tool.get_supported_file_types())
	



