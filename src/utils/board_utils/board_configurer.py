import logging
from pathlib import Path

from ..custom_exceptions.unknown_flasher_type import UnknownFlasherType
from ..wiz_utils import get_remote_configs, read_toml_file_from_url_or_path
from ..wiz_utils.cache_helper import CacheHelper
from .board_config import BoardConfig
from .board_part_id import get_board_part_id
from .board_type import get_board_type

# Import all flashing tool variants
from .flasher_finder import FlasherFinder

# Plain assignment, not the `type X = ...` statement (PEP 695): that syntax
# requires Python 3.12+, but pyproject.toml declares `requires-python = ">=3.10"`.
Cache = dict[str, dict | None]

class BoardConfigurer:
	"""Finds and configures boards automatically
	"""

	# Not a ClassVar: refresh_cache() reassigns this per-instance. The bare
	# annotation (no mutable default) just avoids sharing one list across
	# instances before the first refresh_cache() call.
	_board_cache: list[BoardConfig|None]

	def __init__(self, remote_configs: list[str] | None = None):
		"""Initializes the configurer and builds the initial board cache.

		Args:
			remote_configs (list[str] | None, optional): Local paths and/or
				GitHub URLs of extra board/flashing-tool TOML files, loaded
				in addition to ``config/boards`` and ``config/flashing_tools``.
				Each entry is classified by whether its parsed TOML declares
				a ``board_name`` or ``tool_name`` key (see
				:func:`wiz_utils.get_remote_configs`). Defaults to ``None``
				(no extra configs).
		"""
		self.logger = logging.getLogger(__name__)
		self.remote_configs = remote_configs if remote_configs is not None else []
		self.refresh_cache()

	def refresh_cache(self):
		"""Rebuilds the board cache from the board configuration files on disk.

		``config_cache`` starts from ``CacheHelper.BOARD_CACHE``'s
		integrity-checked on-disk contents (see
		:class:`wiz_utils.cache_helper.CacheHelper`) rather than an empty
		dict, then is written back at the end of the refresh. This memoizes
		each board/flashing-tool config file's parsed TOML both across
		boards within this refresh and across refreshes/app launches, so a
		remote URL already resolved isn't re-fetched on every startup.
		"""
		# Shared across every board below so each remote URL is fetched and
		# parsed at most once per refresh, instead of once per board.
		config_cache: Cache = CacheHelper.BOARD_CACHE.get({})

		self.logger.debug(f"Cache: {config_cache}")

		flasher_finder = FlasherFinder(self.remote_configs, config_cache)
		boards = self.get_boards(self.remote_configs, config_cache)
		self.logger.debug(f"Final config: {config_cache}")
		CacheHelper.BOARD_CACHE.update(config_cache)
		self._board_cache = [self.read_board_config(board, flasher_finder, config_cache) for board in boards]

	def get_board_cache(self) -> list[BoardConfig|None]:
		"""Returns the cached list of parsed board configurations.

		Returns:
			list[BoardConfig]: The board configurations loaded from
				``config/boards``.
		"""
		return self._board_cache

	@staticmethod
	def get_board_configs(remote_configs: list[str], cache: dict[str, dict | None] | None = None) -> list[str]:
		"""Filters ``remote_configs`` down to the ones that declare a board.

		Args:
			remote_configs (list[str]): Local paths and/or GitHub URLs to
				check.
			cache (dict[str, dict | None] | None, optional): Shared memo
				passed through to :func:`wiz_utils.get_remote_configs`.
				Defaults to ``None``.

		Returns:
			list[str]: The subset of ``remote_configs`` whose parsed TOML
				contains a ``board_name`` key.
		"""
		return get_remote_configs(remote_configs, "board_name", cache)

	@staticmethod
	def get_boards(remote_configs: list[str] | None = None, cache: dict[str, dict | None] | None = None) -> list[str]:
		"""Retrieves board configuration files from the config path, plus any remote ones.

		Args:
			remote_configs (list[str] | None, optional): Local paths and/or
				GitHub URLs to check for board configs, in addition to the
				bundled ``config/boards`` folder. Defaults to ``None`` (no
				extra configs).
			cache (dict[str, dict | None] | None, optional): Shared memo
				passed through to :meth:`get_board_configs`. Defaults to
				``None``.

		Returns:
			list[str]: Paths/URLs of all board TOML files found, from both
				``config/boards`` and ``remote_configs``.
		"""
		remote_configs = remote_configs if remote_configs is not None else []

		board_confs: list[str] = BoardConfigurer.get_board_configs(remote_configs, cache)

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
	def read_board_config(conf_file: str, flasher_finder: FlasherFinder, cache: dict[str, dict | None] | None = None) -> BoardConfig|None:
		"""Parses a single board configuration TOML file into a BoardConfig.

		Resolves the board's part ID, board type, and flashing tool
		(via ``flasher_finder``) from the values declared in the file.

		Args:
			conf_file (str): Local path or GitHub URL of the board
				configuration TOML file.
			flasher_finder (FlasherFinder): Already-built flashing tool
				lookup, shared across all boards in a refresh so tool
				discovery only happens once.
			cache (dict[str, dict | None] | None, optional): Shared memo of
				already-resolved remote configs, passed through to
				:func:`wiz_utils.read_toml_file_from_url_or_path`. Defaults
				to ``None``.

		Returns:
			BoardConfig | None: The fully resolved configuration for the
				board, or ``None`` if ``conf_file`` couldn't be read (e.g. a
				failed remote fetch) or declares a ``board_settings.flasher``
				that doesn't match any discovered flashing tool (logged as a
				warning rather than raised).

		Raises:
			UnknownPartID: If ``board_settings.part_id`` is not a known
				:class:`BoardPartID`.
			UnsupportedBoardType: If the resolved flashing tool does not
				support the board's type.
		"""
		logger = logging.getLogger(__name__)
		config_data = read_toml_file_from_url_or_path(conf_file, cache)

		if config_data is None:
			return None

		logger.debug(f"Got config data: {config_data}")

		board_name = config_data["board_name"]

		part_id = get_board_part_id(config_data["board_settings"]["part_id"])

		board_type = get_board_type(config_data["board_settings"]["type"])

		try:
			flashing_tool = flasher_finder.get_flashing_tool(config_data["board_settings"]["flasher"], board_type)
		except UnknownFlasherType:
			logger.warning(f"Unknown Flasher type: {config_data['board_settings']['flasher']}")
			return None

		baud_rate = config_data["board_settings"]["baud_rate"]

		return BoardConfig(board_name, flashing_tool, baud_rate, part_id, board_type, flashing_tool.get_supported_file_types())
	