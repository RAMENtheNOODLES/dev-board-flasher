import os

import pytest
from PySide6.QtCore import QSettings

from utils.wiz_utils.stored_settings import StoredSettings, universal_to_bytes


def test_universal_to_bytes_passes_through_bytes():
	assert universal_to_bytes(b"already bytes") == b"already bytes"


def test_universal_to_bytes_encodes_strings_as_utf8():
	assert universal_to_bytes("hello") == b"hello"


@pytest.mark.parametrize(
	"value",
	[
		0, 1, -1, 65536,
		# Values whose magnitude's bit_length lands exactly on a byte
		# boundary - the previously-buggy case (see stored_settings.py).
		127, 128, 255, -128, -129, 32767, 32768,
	],
)
def test_universal_to_bytes_round_trips_integers(value):
	encoded = universal_to_bytes(value)
	assert isinstance(encoded, bytes)
	assert int.from_bytes(encoded, byteorder="big", signed=True) == value


def test_universal_to_bytes_does_not_treat_bools_as_ints():
	# isinstance(True, int) is True in Python, so this has to be checked
	# explicitly ahead of the int branch or booleans would silently get the
	# wrong (1-byte signed-int) encoding instead of going through the
	# JSON-serializable branch like other non-int JSON types.
	assert universal_to_bytes(True) == b"true"
	assert universal_to_bytes(False) == b"false"


def test_universal_to_bytes_json_encodes_other_serializable_types():
	assert universal_to_bytes([1, 2, 3]) == b"[1, 2, 3]"
	assert universal_to_bytes({"a": 1}) == b'{"a": 1}'
	assert universal_to_bytes(1.5) == b"1.5"


def test_universal_to_bytes_falls_back_to_str_for_non_serializable_objects():
	class NotJsonSerializable:
		def __str__(self):
			return "custom repr"

	assert universal_to_bytes(NotJsonSerializable()) == b"custom repr"


def test_get_set_round_trip(isolated_paths):
	StoredSettings.CHOSEN_BOARD.set("Arduino UNO R3")

	assert StoredSettings.CHOSEN_BOARD.get() == "Arduino UNO R3"


def test_get_set_round_trip_dict(isolated_paths):
	test_val: dict[str, int] = {
		"Ardunio UNO R3" : 0,
		"Other board" : 1,
	}

	temp_store: dict[str, int] = {}

	for key, value in test_val.items():
		temp_store[key] = value
		StoredSettings.CHOSEN_TOOL_SETTING.set(key, value)
		assert StoredSettings.CHOSEN_TOOL_SETTING.get(key, None) == temp_store[key]

	assert StoredSettings.CHOSEN_TOOL_SETTING.get() == temp_store


def test_get_returns_default_when_nothing_stored(isolated_paths):
	assert StoredSettings.CHOSEN_BOARD.get("fallback") == "fallback"


def test_secure_set_get_round_trip(isolated_paths):
	StoredSettings.REMOTE_CONFIGS.secure_set(["a.toml", "b.toml"])

	assert StoredSettings.REMOTE_CONFIGS.secure_get() == ["a.toml", "b.toml"]


def test_secure_get_returns_default_when_nothing_stored(isolated_paths):
	assert StoredSettings.REMOTE_CONFIGS.secure_get(["fallback"]) == ["fallback"]


def test_secure_set_with_ttl_zero_expires_immediately(isolated_paths):
	StoredSettings.REMOTE_CONFIGS.secure_set(["a.toml"], ttl_seconds=0)

	assert StoredSettings.REMOTE_CONFIGS.secure_get(["fallback"]) == ["fallback"]


def test_secure_set_with_no_ttl_never_expires(isolated_paths):
	# ttl_seconds defaults to None, which diskcache treats as "no expiry".
	StoredSettings.REMOTE_CONFIGS.secure_set(["a.toml"])

	assert StoredSettings.REMOTE_CONFIGS.secure_get() == ["a.toml"]


# --- backup_settings -------------------------------------------------------


def test_backup_settings_copies_current_values_to_a_bak_file(isolated_paths):
	StoredSettings.CHOSEN_BOARD.set("Arduino UNO R3")

	StoredSettings.backup_settings()

	backup_path = StoredSettings.get_config_path() + ".bak"
	assert os.path.isfile(backup_path)
	backup = QSettings(backup_path, QSettings.Format.IniFormat)
	assert backup.value(StoredSettings.CHOSEN_BOARD.value) == "Arduino UNO R3"


def test_backup_settings_numbers_the_backup_instead_of_overwriting_an_existing_one(isolated_paths):
	StoredSettings.CHOSEN_BOARD.set("Arduino UNO R3")
	StoredSettings.backup_settings()  # writes config_path + ".bak"

	StoredSettings.CHOSEN_BOARD.set("Changed After First Backup")
	StoredSettings.backup_settings()  # should not clobber the ".bak" above

	first_backup = QSettings(StoredSettings.get_config_path() + ".bak", QSettings.Format.IniFormat)
	second_backup = QSettings(StoredSettings.get_config_path() + ".bak0", QSettings.Format.IniFormat)
	assert first_backup.value(StoredSettings.CHOSEN_BOARD.value) == "Arduino UNO R3"
	assert second_backup.value(StoredSettings.CHOSEN_BOARD.value) == "Changed After First Backup"


# --- transfer_legacy_settings ------------------------------------------------


def test_transfer_legacy_settings_copies_old_flat_key_to_new_sectioned_key(isolated_paths):
	settings = QSettings(StoredSettings.get_config_path(), QSettings.Format.IniFormat)
	# Simulate a value still stored under its pre-sections flat key name
	# (StoredSettings.CHOSEN_BOARD's current key is "board_flashing/selected_board").
	settings.setValue("selected_board", "LegacyBoard")
	settings.sync()

	StoredSettings.transfer_legacy_settings()

	assert StoredSettings.CHOSEN_BOARD.get() == "LegacyBoard"


def test_transfer_legacy_settings_leaves_new_settings_untouched_when_no_legacy_value(isolated_paths):
	StoredSettings.CHOSEN_BOARD.set("AlreadyMigrated")

	StoredSettings.transfer_legacy_settings()

	assert StoredSettings.CHOSEN_BOARD.get() == "AlreadyMigrated"


def test_transfer_legacy_settings_backs_up_settings_first(isolated_paths):
	StoredSettings.CHOSEN_BOARD.set("Arduino UNO R3")

	StoredSettings.transfer_legacy_settings()

	assert os.path.isfile(StoredSettings.get_config_path() + ".bak")


def test_transfer_legacy_settings_sets_the_migrated_flag(isolated_paths):
	StoredSettings.CHOSEN_BOARD.set("Arduino UNO R3")

	StoredSettings.transfer_legacy_settings()

	assert StoredSettings.NEW_SETTINGS.get(False) is True


def test_transfer_legacy_settings_does_not_rerun_once_already_migrated(isolated_paths):
	StoredSettings.CHOSEN_BOARD.set("Arduino UNO R3")
	StoredSettings.transfer_legacy_settings()  # writes config_path + ".bak"

	StoredSettings.CHOSEN_BOARD.set("Changed After First Migration")
	StoredSettings.transfer_legacy_settings()  # should be a no-op this time

	# A second real run would back up again, landing at ".bak0"; its absence
	# proves the NEW_SETTINGS guard actually short-circuited the rerun.
	assert not os.path.exists(StoredSettings.get_config_path() + ".bak0")
	assert StoredSettings.CHOSEN_BOARD.get() == "Changed After First Migration"


# --- import_settings / export_settings --------------------------------------


def test_export_settings_writes_every_stored_setting_to_the_given_file(isolated_paths, tmp_path):
	StoredSettings.CHOSEN_BOARD.set("Arduino UNO R3")
	StoredSettings.CAN_DBC_FILE.set("engine.dbc")
	export_path = str(tmp_path / "exported.ini")

	StoredSettings.export_settings(export_path)

	exported = QSettings(export_path, QSettings.Format.IniFormat)
	assert exported.value(StoredSettings.CHOSEN_BOARD.value) == "Arduino UNO R3"
	assert exported.value(StoredSettings.CAN_DBC_FILE.value) == "engine.dbc"


def test_export_settings_merges_into_an_existing_file_rather_than_replacing_it(isolated_paths, tmp_path):
	export_path = str(tmp_path / "exported.ini")
	preexisting = QSettings(export_path, QSettings.Format.IniFormat)
	preexisting.setValue("untouched/preexisting_key", "keep me")
	preexisting.sync()
	StoredSettings.CHOSEN_BOARD.set("Arduino UNO R3")

	StoredSettings.export_settings(export_path)

	exported = QSettings(export_path, QSettings.Format.IniFormat)
	assert exported.value("untouched/preexisting_key") == "keep me"
	assert exported.value(StoredSettings.CHOSEN_BOARD.value) == "Arduino UNO R3"


def test_import_settings_replaces_stored_settings_with_the_files_contents(isolated_paths, tmp_path):
	StoredSettings.CHOSEN_BOARD.set("StaleBoard")
	import_path = str(tmp_path / "to_import.ini")
	source = QSettings(import_path, QSettings.Format.IniFormat)
	source.setValue(StoredSettings.CHOSEN_BOARD.value, "ImportedBoard")
	source.sync()

	StoredSettings.import_settings(import_path)

	assert StoredSettings.CHOSEN_BOARD.get() == "ImportedBoard"


def test_import_settings_removes_keys_not_present_in_the_imported_file(isolated_paths, tmp_path):
	StoredSettings.CHOSEN_BOARD.set("Arduino UNO R3")
	StoredSettings.CAN_DBC_FILE.set("engine.dbc")
	import_path = str(tmp_path / "to_import.ini")
	source = QSettings(import_path, QSettings.Format.IniFormat)
	source.setValue(StoredSettings.CHOSEN_BOARD.value, "ImportedBoard")
	source.sync()

	StoredSettings.import_settings(import_path)

	assert StoredSettings.CHOSEN_BOARD.get() == "ImportedBoard"
	assert StoredSettings.CAN_DBC_FILE.get() is None


def test_import_settings_backs_up_settings_first(isolated_paths, tmp_path):
	StoredSettings.CHOSEN_BOARD.set("Arduino UNO R3")
	import_path = str(tmp_path / "to_import.ini")
	QSettings(import_path, QSettings.Format.IniFormat).sync()

	StoredSettings.import_settings(import_path)

	backup = QSettings(StoredSettings.get_config_path() + ".bak", QSettings.Format.IniFormat)
	assert backup.value(StoredSettings.CHOSEN_BOARD.value) == "Arduino UNO R3"


# --- clear_settings_in_group ------------------------------------------------


def test_clear_settings_in_group_removes_only_that_groups_keys(isolated_paths):
	StoredSettings.CHOSEN_BOARD.set("Arduino UNO R3")
	StoredSettings.CAN_DBC_FILE.set("engine.dbc")

	StoredSettings.clear_settings_in_group("board_flashing")

	assert StoredSettings.CHOSEN_BOARD.get() is None
	assert StoredSettings.CAN_DBC_FILE.get() == "engine.dbc"


def test_clear_settings_in_group_removes_all_keys_in_that_group(isolated_paths):
	StoredSettings.CAN_DBC_FILE.set("engine.dbc")
	StoredSettings.CAN_BAUD_RATE.set(500000)

	StoredSettings.clear_settings_in_group("can_settings")

	assert StoredSettings.CAN_DBC_FILE.get() is None
	assert StoredSettings.CAN_BAUD_RATE.get() is None


def test_clear_settings_in_group_is_a_noop_for_an_empty_group(isolated_paths):
	StoredSettings.CHOSEN_BOARD.set("Arduino UNO R3")

	StoredSettings.clear_settings_in_group("no_such_group")

	assert StoredSettings.CHOSEN_BOARD.get() == "Arduino UNO R3"
