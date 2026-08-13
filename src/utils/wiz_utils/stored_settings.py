from typing import Any

from enum import Enum, unique
from PySide6.QtCore import QSettings

import logging

@unique
class StoredSettings(Enum):
	"""Keys for values persisted across app launches via ``QSettings``.

	Each member's value is the underlying ``QSettings`` key. Requires
	``QCoreApplication``'s organization/application name to already be set
	(see :class:`main.MainWindow`) so values are stored under the
	``CookieJAR``/``wizlog`` scope.
	"""

	CACHED_FILE_TO_FLASH = "flash_file"
	EXTERNAL_TOOL_FOLDER = "ext_tools"
	EXTERNAL_BOARDS_FOLDER = "ext_boards"
	CHOSEN_BAUD_RATE = "baud_rate"
	CHOSEN_BOARD = "selected_board"
	CHOSEN_TOOL_SETTING = "tool_setting"
	REMOTE_CONFIGS = "remote_configs"

	# CAN Settings
	CAN_DBC_FILE = "dbc_file"

	def get(self, default_val: Any = None) -> Any:
		"""Retrieves this setting's stored value.

		Returns:
			Any: The stored value, or ``None`` if nothing has been saved yet.
		"""
		logger = logging.getLogger(__name__)
		settings = QSettings()

		out = settings.value(self.value, default_val)
		logger.debug(f"Retrieving setting ({self.name} [{self.value}]) with value: {out}")
		return out

	def set(self, value: Any) -> None:
		"""Persists a new value for this setting.

		Args:
			value (Any): The value to store.
		"""
		logger = logging.getLogger(__name__)
		settings = QSettings()

		logger.debug(f"Setting setting ({self.name} [{self.value}]) with value: {value}")
		settings.setValue(self.value, value)