import json
import logging
import os
import sys
from enum import Enum, unique
from typing import Any, overload

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
	and application name (:meth:`transfer_settings_to_file` handled migrating
	values left over from that legacy location, but is no longer called from
	app startup); :meth:`transfer_legacy_settings` instead migrates values
	stored under each member's older flat key (before sections were
	introduced) to its current sectioned one, the first time the app runs
	after upgrading. Secrets needing at-rest encryption (currently just
	:attr:`STORED_CACHE_HASHES`) instead go through :meth:`secure_get`/
	:meth:`secure_set`, which store a Fernet-encrypted, TTL-limited value in
	a `diskcache` alongside the INI file, keyed off an encryption key kept
	in the OS credential store (via ``keyring``).
	"""

	CACHED_FILE_TO_FLASH = "board_flashing/flash_file"
	CHOSEN_BAUD_RATE = "board_flashing/baud_rate"
	CHOSEN_BOARD = "board_flashing/selected_board"
	CHOSEN_TOOL_SETTING = "board_flashing/tool_setting"
	CHOSEN_TOOL_SUB_SETTING = "board_flashing/tool_sub_setting"
	REMOTE_CONFIGS = "board_flashing/remote_configs"

	# App Preferences
	APP_FONT = "preferences/app_font"
	APP_FONT_SIZE = "preferences/app_font_size"

	# CAN Settings
	CAN_DBC_FILE = "can_settings/dbc_file"
	CAN_BAUD_RATE = "can_settings/can_baud_rate"
	CAN_DM1_SPN_FILE = "can_settings/dm1_spn_file"
	CAN_DM1_FMI_FILE = "can_settings/dm1_fmi_file"
	CAN_TX_MESSAGES = "can_settings/tx_messages"

	# ELF Parser Settings
	ELF_FILE = "elf_settings/elf_file"

	# A2L Parser Settings
	A2L_FILE = "a2l_settings/a2l_file"

	# Cache Settings
	STORED_CACHE_HASHES = "protected/cache_hashes"

	# App related settings (private)
	NEW_SETTINGS = "app/settings_migrated"
	"""Internal flag set by :meth:`transfer_legacy_settings` once it has migrated flat keys to sectioned ones, so it only runs once."""

	@overload
	def get(self, key: str, default_val: Any = None) -> Any: ...

	@overload
	def get(self, default_val: Any = None) -> Any: ...

	def get(self, *args: Any, **kwargs: Any) -> Any:
		logger = logging.getLogger(__name__)
		settings = QSettings(self.get_config_path(), QSettings.Format.IniFormat)

		dict_mode = False

		key: Any = None
		default_val: Any = None

		if len(args) == 2:
			key, default_val = args
			dict_mode = True
		elif len(args) == 1:
			default_val = args[0]
		elif "key" in kwargs or "default_val" in kwargs:
			key = kwargs.get("key")
			default_val = kwargs.get("default_val")

			if key:
				dict_mode = True

		if dict_mode:
			try:
				out_dict: dict[str, Any] = dict(settings.value(self.value))
				logger.debug(f"Retrieving setting ({self.name} [{self.value}]) with value: {out_dict}")
				return out_dict.get(key, default_val)
			except (ValueError, TypeError):
				logger.exception("Error")
				return default_val
		else:
			out_non_dict: Any = settings.value(self.value, default_val)
			logger.debug(f"Retrieving setting ({self.name} [{self.value}]) with value: {out_non_dict}")
			return out_non_dict
			
	@overload
	def set(self, key: str, value: Any) -> None: ...

	@overload
	def set(self, value: Any) -> None:
		"""Persists a new value for this setting.

		Args:
			value (Any): The value to store.
		"""

	def set(self, *args: Any, **kwargs: Any) -> None:
		logger = logging.getLogger(__name__)
		settings = QSettings(self.get_config_path(), QSettings.Format.IniFormat)

		dict_mode = False

		key: Any = None
		value: Any = None

		if len(args) == 2:
			key, value = args
			dict_mode = True
		elif len(args) == 1:
			value = args[0]
		elif "key" in kwargs or "value" in kwargs:
			key = kwargs.get("key")
			value = kwargs.get("value")

			if key:
				dict_mode = True

		logger.debug(f"Applying setting ({self.name} [{self.value}]) with value: {value}")
		if dict_mode:
			try:
				modified_value = self.get({})
				if (isinstance(modified_value, str)):
					modified_value = {}
				modified_value[key] = value
				settings.setValue(self.value, modified_value)
			except (ValueError, TypeError):
				logger.exception("Error")
				return
		else:
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
		"""Returns the OS's standard per-user documents directory."""
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
	def backup_settings() -> None:
		"""Copies every current setting into a sibling ``.bak``-suffixed INI file, used by :meth:`transfer_legacy_settings`.

		The backup is written next to the real settings file, at
		:meth:`get_config_path` with ``.bak`` appended, or ``.bak0``,
		``.bak1``, ... if that path is already taken (e.g. by a previous
		backup that hasn't been cleaned up), so an existing backup is never
		overwritten.
		"""
		logger = logging.getLogger(__name__)
		current_settings = QSettings(StoredSettings.get_config_path(), QSettings.Format.IniFormat)

		base_backup_ext = ".bak"
		counter = 0

		while os.path.exists(StoredSettings.get_config_path() + base_backup_ext):
			base_backup_ext = f".bak{counter}"
			counter += 1

		backup_path = StoredSettings.get_config_path() + base_backup_ext

		logger.info(f"Backing up settings to {backup_path}")

		backup_settings = QSettings(backup_path, QSettings.Format.IniFormat)

		for key in current_settings.allKeys():
			value = current_settings.value(key)
			logger.info(f"Backing up: {key} : {value}")

			backup_settings.setValue(key, value)

	@staticmethod
	def import_settings(file_path: str) -> None:
		"""Replaces every stored setting with the contents of an external INI file, used by **Preferences > Import Settings**.

		The current settings file is first backed up via
		:meth:`backup_settings`, then wiped and repopulated with every key
		found in ``file_path``. Keys the current settings have that
		``file_path`` doesn't are removed (not merged), so this is a full
		replace rather than an overlay; see :meth:`export_settings` for the
		inverse operation.

		Args:
			file_path (str): Path to the INI file to import from (typically
				one previously written by :meth:`export_settings`).
		"""
		logger = logging.getLogger(__name__)
		settings = QSettings(StoredSettings.get_config_path(), QSettings.Format.IniFormat)
		StoredSettings.backup_settings()
		settings.clear()
		
		import_settings = QSettings(file_path, QSettings.Format.IniFormat)
		logger.info(f"Importing current settings from {file_path}")
		
		for key in import_settings.allKeys():
			value = import_settings.value(key)
		
			settings.setValue(key, value)
		
		logger.info("Done importing settings...")

	@staticmethod
	def export_settings(file_path: str) -> None:
		"""Copies every stored setting to an external INI file, used by **Preferences > Export Settings**.

		Unlike :meth:`backup_settings`, the destination is caller-chosen
		(typically picked via a file dialog) rather than an auto-numbered
		sibling of the real settings file, and any existing content at
		``file_path`` is merged with rather than replaced by the export
		(matching keys are overwritten, others are left alone).

		Args:
			file_path (str): Path to the INI file to write the current
				settings to.
		"""
		logger = logging.getLogger(__name__)
		settings = QSettings(StoredSettings.get_config_path(), QSettings.Format.IniFormat)

		export_settings = QSettings(file_path, QSettings.Format.IniFormat)
		logger.info(f"Exporting current settings to {file_path}")

		for key in settings.allKeys():
			value = settings.value(key)

			export_settings.setValue(key, value)

		logger.info("Done exporting settings...")

	@staticmethod
	def clear_all_settings() -> None:
		"""Wipes every stored setting, used by the **Edit > Clear All Settings** menu action."""
		logger = logging.getLogger(__name__)
		settings = QSettings(StoredSettings.get_config_path(), QSettings.Format.IniFormat)
		logger.info("Clearing ALL settings...")
		settings.clear()
		settings.sync()
		logger.info("Done clearing ALL settings...")

	@staticmethod
	def transfer_legacy_settings() -> None:
		"""One-time migration of settings stored under their old flat INI keys to the new sectioned ones.

		Older builds stored each setting directly under its bare key (e.g.
		``selected_board``); :class:`StoredSettings` members now store it
		under a sectioned key instead (e.g. ``board_flashing/selected_board``,
		see the class docstring). Run as the first :class:`main.MainWindow`
		load task on every startup (in place of :meth:`transfer_settings_to_file`,
		which handled the earlier registry-to-INI migration and is no longer
		called), this is a no-op if :attr:`NEW_SETTINGS` is already ``True``
		(i.e. this has already run once); otherwise it backs up the settings
		file via :meth:`backup_settings`, then for each :class:`StoredSettings`
		member copies any value still present under its old flat key over to
		its new sectioned key, and finally sets :attr:`NEW_SETTINGS` so it
		won't repeat the backup/migration on the next startup. Old values are
		left in place unless running from a compiled build, to avoid wiping
		them before this migration itself has shipped in a release. Compiled
		builds are detected via ``"__compiled__" in globals()``, the flag
		Nuitka injects (this project is packaged with Nuitka, not PyInstaller).
		"""
		logger = logging.getLogger(__name__)
		settings = QSettings(StoredSettings.get_config_path(), QSettings.Format.IniFormat)

		has_migrated = StoredSettings.NEW_SETTINGS.get(False)
		logger.debug(f"Has migrated: {has_migrated}")
		if has_migrated:
			logger.info("Settings already migrated...")
			return

		StoredSettings.backup_settings()

		new_settings = [member.value for member in StoredSettings]
		old_settings = [member.value.split("/")[1] for member in StoredSettings]

		logger.debug(f"Found new settings: ({new_settings}) and old settings: ({old_settings})")

		logger.debug(f"Setting Keys: {settings.allKeys()}")

		for old_setting, new_setting in zip(old_settings, new_settings):
			logger.debug(f"Old setting: {old_setting}, New Setting: {new_setting}")
			old_setting_value = settings.value(old_setting)
			logger.debug(f"Old setting value: {old_setting_value}")

			if old_setting_value is not None:
				logger.debug(f"Found old setting ({old_setting}) with value: {old_setting_value}, transferring to new setting: {new_setting}")
				settings.setValue(new_setting, old_setting_value)

				if "__compiled__" in globals():
					# Only remove the old settings when running from a compiled build.
					# This should (hopefully) prevent settings from being wiped before this update releases
					settings.remove(old_setting)

		logger.info("Done migrating settings...")
		StoredSettings.NEW_SETTINGS.set(True)

	@staticmethod
	def clear_settings_in_group(group: str) -> None:
		"""Wipes every stored setting under a single group, leaving the rest of the settings file untouched.

		Unlike :meth:`clear_all_settings`, which wipes the whole settings
		file, this only removes keys whose section matches ``group``, using
		``QSettings.beginGroup``/``endGroup`` to scope the removal to that
		prefix.

		Args:
			group (str): The section name to clear, i.e. the part of a
				:class:`StoredSettings` member's key before its ``/`` (e.g.
				``"can_settings"`` to wipe :attr:`CAN_DBC_FILE` and
				:attr:`CAN_BAUD_RATE` without touching any other group).
		"""
		logger = logging.getLogger(__name__)
		settings = QSettings(StoredSettings.get_config_path(), QSettings.Format.IniFormat)

		settings.beginGroup(group)
		for key in settings.allKeys():
			logger.info(f"Removing key ({key}) in group ({group})")
			settings.remove(key)
		settings.endGroup()
