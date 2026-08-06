import tomllib
from pathlib import Path

from .board_config import BoardConfig
from .board_type import BoardType
from .board_part_id import BoardPartID

from ..custom_exceptions import UnsupportedBoardType, UnknownFlasherType, UnknownPartID

# Import all flashing tool variants
from ..flashing_tools import BaseFlashingTool, AVRDude, ESP32


class BoardConfigurer:
	"""Finds and configures boards automatically
	"""

	_board_cache: list[BoardConfig] = []

	def __init__(self):
		self.refresh_cache()

	def refresh_cache(self):
		boards = self.get_boards()
		self._board_cache = [self.read_board_config(board) for board in boards]

	def get_board_cache(self) -> list[BoardConfig]:
		return self._board_cache

	@staticmethod
	def get_boards() -> list[str]:
		"""Retrieves board configuration files from the config path

		Returns:
			list[str]: A list of all files found in the config/boards folder
		"""

		current_dir = Path(__file__).resolve().parent
		config_path = current_dir.parent.parent.parent / "Config" / "boards"

		board_confs: list[str] = [str(f) for f in config_path.iterdir() if (f.is_file() and f.suffix == ".toml")]

		return board_confs

	@staticmethod
	def get_board_type(board_type: str) -> BoardType:

		if (board_type.upper() in BoardType.__members__):
			return BoardType[board_type.upper()]
		else:
			return BoardType.UNKNOWN

	@staticmethod
	def get_board_part_id(board_part_id: str) -> BoardPartID:
		if (board_part_id.upper() in BoardPartID.__members__):
			return BoardPartID[board_part_id.upper()]
		else:
			raise UnknownPartID(board_part_id)

	@staticmethod
	def get_flashing_tool(flasher_name: str, board_type: BoardType) -> BaseFlashingTool:
		match flasher_name.lower():
			case "avrdude":
				out = AVRDude()
			case "esp32":
				out = ESP32()
			case _:
				raise UnknownFlasherType(flasher_name)

		if (board_type in out.get_supported_boards()):
			return out
		else:
			raise UnsupportedBoardType(board_type, out)

	@staticmethod
	def read_board_config(conf_file: str) -> BoardConfig:
		with open(conf_file, "rb") as f:
			config_data = tomllib.load(f)

		print(f"Got config data: {config_data}")

		board_name = config_data["board_name"]

		part_id = BoardConfigurer.get_board_part_id(config_data["board_settings"]["part_id"])

		board_type = BoardConfigurer.get_board_type(config_data["board_settings"]["type"])

		flashing_tool = BoardConfigurer.get_flashing_tool(config_data["board_settings"]["flasher"], board_type)

		baud_rate = config_data["board_settings"]["baud_rate"]

		return BoardConfig(board_name, flashing_tool, baud_rate, part_id, board_type, flashing_tool.get_supported_file_types())
	



