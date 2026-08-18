import json
import logging
import os
import sys
from enum import Enum, unique
from typing import Any

import keyring
from cryptography.fernet import Fernet
from diskcache import Cache
from PySide6.QtCore import QSettings, QStandardPaths

if sys.platform == "win32":
	# keyring normally picks a backend via importlib.metadata entry point
	# discovery, which the Nuitka onefile build doesn't preserve unless
	# distribution metadata is explicitly bundled. Pinning the backend
	# directly sidesteps that so it behaves the same in source and
	# compiled builds.
	from keyring.backends.Windows import WinVaultKeyring
	keyring.set_keyring(WinVaultKeyring())

_SETTINGS_FILE = "flash_wiz_settings.ini"
_SERVICE_NAME = "dev-board-flasher"
_USERNAME = "flashwiz_stored_settings_key"

_SECURE_SETTINGS = ["remote_configs"]

def universal_to_bytes(variable):
	"""Best-effort coercion of ``variable`` to ``bytes``, for feeding to :class:`~cryptography.fernet.Fernet`.

	``diskcache`` can hand back a value as ``bytes``, ``str``, or ``int``
	depending on how it chose to serialize it internally, so
	:meth:`StoredSettings.secure_get` normalizes through this before
	decrypting rather than assuming a single type.
	"""
	# 1. Handle existing bytes
	if isinstance(variable, bytes):
		return variable
	# 2. Handle strings
	if isinstance(variable, str):
		return variable.encode('utf-8')
	# 3. Handle integers
	if isinstance(variable, int) and not isinstance(variable, bool):
		# bit_length() excludes the sign bit, so a value needs a full extra
		# byte once its magnitude's bit_length lands exactly on a byte
		# boundary (128, 255, -129, ...) - the previous "+ 7 // 8" rounding
		# didn't account for that and could overflow to_bytes for those
		# values. This always allocates enough (occasionally one byte more
		# than the true minimum for a negative power-of-two boundary like
		# -128, which still round-trips correctly, just not maximally
		# compact) rather than risk under-allocating again.
		byte_length = variable.bit_length() // 8 + 1
		return variable.to_bytes(byte_length, byteorder='big', signed=True)
	# 4. Handle JSON-serializable types (lists, dicts, floats, bools)
	try:
		return json.dumps(variable).encode('utf-8')
	except (TypeError, OverflowError):
		# 5. Fallback for custom objects / complex types
		return str(variable).encode('utf-8')

@unique
class StoredSettings(Enum):
	"""Keys for values persisted across app launches.

	Each member's value is the underlying storage key. Plain settings (via
	:meth:`get`/:meth:`set`) are stored in an INI file under
	:meth:`get_config_path` (the OS's standard per-user config directory,
	via ``QStandardPaths``), rather than the registry/``QSettings`` default
	scope previously used under the ``CookieJAR``/``wizlog`` organization
	and application name; :meth:`transfer_settings_to_file` migrates any
	values left over from that legacy location the first time the app runs
	after upgrading. Secrets needing at-rest encryption (currently just
	:attr:`STORED_CACHE_HASHES`) instead go through :meth:`secure_get`/
	:meth:`secure_set`, which store a Fernet-encrypted, TTL-limited value in
	a `diskcache` alongside the INI file, keyed off an encryption key kept
	in the OS credential store (via ``keyring``).
	"""

	CACHED_FILE_TO_FLASH = "flash_file"
	CHOSEN_BAUD_RATE = "baud_rate"
	CHOSEN_BOARD = "selected_board"
	CHOSEN_TOOL_SETTING = "tool_setting"
	REMOTE_CONFIGS = "remote_configs"

	# CAN Settings
	CAN_DBC_FILE = "dbc_file"
	CAN_BAUD_RATE = "can_baud_rate"

	# ELF Parser Settings
	ELF_FILE = "elf_file"

	# Cache Settings
	STORED_CACHE_HASHES = "cache_hashes"

	def get(self, default_val: Any = None) -> Any:
		"""Retrieves this setting's stored value.

		Returns:
			Any: The stored value, or ``None`` if nothing has been saved yet.
		"""
		logger = logging.getLogger(__name__)
		settings = QSettings(self.get_config_path(), QSettings.Format.IniFormat)

		out = settings.value(self.value, default_val)
		logger.debug(f"Retrieving setting ({self.name} [{self.value}]) with value: {out}")
		return out

	def set(self, value: Any) -> None:
		"""Persists a new value for this setting.

		Args:
			value (Any): The value to store.
		"""
		logger = logging.getLogger(__name__)
		settings = QSettings(self.get_config_path(), QSettings.Format.IniFormat)

		logger.debug(f"Setting setting ({self.name} [{self.value}]) with value: {value}")
		settings.setValue(self.value, value)

	@staticmethod
	def does_encryption_key_exist() -> bool:
		"""Returns whether the Fernet key used by :meth:`secure_get`/:meth:`secure_set` has been generated yet."""
		return keyring.get_password(_SERVICE_NAME, _USERNAME) is not None

	def secure_set(self, value: Any, ttl_seconds: int|None = None) -> None:
		"""Encrypts and persists a value for this setting with a time limit.

		Unlike :meth:`set`, the value is JSON-encoded then encrypted with a
		Fernet key stored in the OS credential store (generated on first
		use) before being written to a `diskcache` alongside the settings
		INI file. Intended for values that are sensitive but shouldn't be
		trusted indefinitely once written (e.g. :attr:`STORED_CACHE_HASHES`,
		so a stale hash can't be used to validate a cache file forever).

		Args:
			value (Any): The JSON-serializable value to store.
			ttl_seconds (int): How long, in seconds, the value remains
				readable via :meth:`secure_get` before it's treated as
				expired. ``0`` expires it immediately.
		"""
		settings_path = StoredSettings.get_settings_path()
		cache = Cache(settings_path)
		logger = logging.getLogger(__name__)

		if not self.does_encryption_key_exist():
			keyring.set_password(_SERVICE_NAME, _USERNAME, Fernet.generate_key().decode())

		key = keyring.get_password(_SERVICE_NAME, _USERNAME)

		# Key should always have a value
		assert key is not None

		try:
			cipher = Fernet(key)
		except ValueError:
			keyring.set_password(_SERVICE_NAME, _USERNAME, Fernet.generate_key().decode())
			logger.exception("Value Error")
			sys.exit(-1)

		encrypted_value = cipher.encrypt(json.dumps(value).encode("utf-8"))
		
		logger.debug(f"Setting setting ({self.name} [{self.value}]) with value: {encrypted_value}")
		cache.set(self.name, encrypted_value, ttl_seconds)

	def secure_get(self, default_val: Any = None) -> Any:
		"""Retrieves and decrypts this setting's value, as previously stored via :meth:`secure_set`.

		Args:
			default_val (Any, optional): Value to return if nothing has been
				stored yet, or if the stored value has expired past its
				``ttl_seconds``. Defaults to ``None``.

		Returns:
			Any: The decrypted, JSON-decoded value, or ``default_val``.
		"""
		settings_path = StoredSettings.get_settings_path()
		cache = Cache(settings_path)
		logger = logging.getLogger(__name__)
		if not self.does_encryption_key_exist():
			keyring.set_password(_SERVICE_NAME, _USERNAME, Fernet.generate_key().decode())
			return default_val

		key = keyring.get_password(_SERVICE_NAME, _USERNAME)
	
		# Key should always have a value
		assert key is not None

		try:
			cipher = Fernet(key)
		except ValueError:
			keyring.set_password(_SERVICE_NAME, _USERNAME, Fernet.generate_key().decode())
			logger.exception("Value Error")
			sys.exit(-1)

		_MISSING = object()
		out = cache.get(self.name, _MISSING)
		if out is _MISSING:
			logger.debug(f"No stored value for setting ({self.name} [{self.value}]); using default.")
			return default_val

		logger.debug(f"Retrieving setting ({self.name} [{self.value}]) with value: {out}")

		decrypted = cipher.decrypt(universal_to_bytes(out))
		return json.loads(decrypted.decode("utf-8"))

	@staticmethod
	def get_settings_path() -> str:
		"""Returns the OS's standard per-user config directory used to hold app settings and the secure cache."""
		return QStandardPaths.writableLocation(QStandardPaths.StandardLocation.ConfigLocation)

	@staticmethod
	def get_config_path() -> str:
		"""Returns the absolute path of the settings INI file, creating its parent directory if needed."""
		settings_path = StoredSettings.get_settings_path()
		# ensure the directory exists
		os.makedirs(settings_path, exist_ok=True)
		# Get the absolute path
		return os.path.join(settings_path, _SETTINGS_FILE)

	@staticmethod
	def get_documents_path() -> str:
		"""REturns the OS's standard per-user documents directory."""
		return QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)

	@staticmethod
	def transfer_settings_to_file():
		"""One-time migration of settings from the legacy registry/``QSettings`` location into the INI file.

		Older builds stored settings via bare ``QSettings("CookieJAR",
		"wizlog")``, which resolves to the Windows registry. Run as the
		first :class:`main.MainWindow` load task on every startup, this
		copies any keys still there into the INI file at
		:meth:`get_config_path` and clears the registry location, but only
		if that INI file doesn't already exist — so it's a no-op after the
		first run post-upgrade, and never overwrites values already
		migrated.
		"""
		logger = logging.getLogger(__name__)
		registry_settings = QSettings("CookieJAR", "wizlog") # Legacy settings path

		config_path = StoredSettings.get_config_path()

		if not os.path.isfile(config_path):
			logger.info("Migrating Registry Settings...")
			logger.info(f"Storing settings in: {config_path}")
			file_settings = QSettings(config_path, QSettings.Format.IniFormat)

			for key in registry_settings.allKeys():
				value = registry_settings.value(key)
				logger.info(f"Transferring key ({key}) with value ({value}).")
				if key in _SECURE_SETTINGS:
					StoredSettings[key].secure_set(value)
				else:
					file_settings.setValue(key, value)

			file_settings.sync()

			registry_settings.clear()
			registry_settings.sync()
			logger.info("Done transferring settings...")
		else:
			logger.info("Settings already migrated...")

	@staticmethod
	def clear_all_settings() -> None:
		"""Wipes every stored setting, used by the **Edit > Clear All Settings** menu action."""
		logger = logging.getLogger(__name__)
		settings = QSettings(_SETTINGS_FILE, QSettings.Format.IniFormat)
		logger.info("Clearing ALL settings...")
		settings.clear()
		settings.sync()
		logger.info("Done clearing ALL settings...")