import pytest
from PySide6.QtCore import QSettings
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QFileDialog, QMessageBox

import preferences
from preferences import Preferences
from utils.wiz_utils.stored_settings import StoredSettings

pytestmark = pytest.mark.integration


def _fake_font_resource(monkeypatch, family="Fira Code NF"):
	monkeypatch.setattr(QFontDatabase, "addApplicationFont", staticmethod(lambda path: 0))
	monkeypatch.setattr(QFontDatabase, "applicationFontFamilies", staticmethod(lambda font_id: [family]))


def test_update_font_stages_the_chosen_font(qapp, isolated_paths):
	dlg = Preferences(None)

	dlg.update_font(QFont("Consolas", 14))

	assert dlg.chosenFont.family() == "Consolas"
	assert dlg.chosenFont.pointSize() == 14


def test_font_size_changed_stages_the_chosen_size(qapp, isolated_paths):
	dlg = Preferences(None)

	dlg.font_size_changed(18)

	assert dlg.chosenFontSize == 18


def test_save_settings_btn_persists_the_chosen_font_and_size_and_prompts_a_restart(qapp, isolated_paths, monkeypatch):
	shown = []
	monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *args, **kwargs: shown.append(args)))
	dlg = Preferences(None)
	dlg.chosenFont = QFont("Consolas", 14)
	dlg.chosenFontSize = 18

	dlg.save_settings_btn()

	stored_font = StoredSettings.APP_FONT.get()
	assert stored_font.family() == "Consolas"
	assert StoredSettings.APP_FONT_SIZE.get() == 18
	assert len(shown) == 1


def test_clear_all_settings_btn_clears_settings_when_confirmed(qapp, isolated_paths, monkeypatch):
	monkeypatch.setattr(
		QMessageBox, "critical", staticmethod(lambda *args, **kwargs: QMessageBox.StandardButton.Yes)
	)
	StoredSettings.CHOSEN_BOARD.set("Arduino UNO R3")
	dlg = Preferences(None)

	dlg.clear_all_settings_btn()

	assert StoredSettings.CHOSEN_BOARD.get() is None


def test_clear_all_settings_btn_does_nothing_when_cancelled(qapp, isolated_paths, monkeypatch):
	monkeypatch.setattr(
		QMessageBox, "critical", staticmethod(lambda *args, **kwargs: QMessageBox.StandardButton.Cancel)
	)
	StoredSettings.CHOSEN_BOARD.set("Arduino UNO R3")
	dlg = Preferences(None)

	dlg.clear_all_settings_btn()

	assert StoredSettings.CHOSEN_BOARD.get() == "Arduino UNO R3"


# --- reset (init + post-revert refresh) -------------------------------------


def test_reset_applies_the_stored_font_family_override_on_init(qapp, isolated_paths, monkeypatch):
	_fake_font_resource(monkeypatch)
	StoredSettings.APP_FONT.set(QFont("Consolas", 99))  # size on the stored QFont itself is ignored

	dlg = Preferences(None)

	assert dlg.chosenFont.family() == "Consolas"
	assert dlg.chosenFont.pointSize() == 11
	assert dlg.chosenFontSize == 11
	assert dlg.fontSizeBox.value() == 11


def test_reset_applies_the_stored_font_size_override_on_init(qapp, isolated_paths, monkeypatch):
	_fake_font_resource(monkeypatch)
	StoredSettings.APP_FONT_SIZE.set(20)

	dlg = Preferences(None)

	assert dlg.chosenFontSize == 20
	assert dlg.fontSizeBox.value() == 20
	assert dlg.chosenFont.pointSize() == 20


def test_reset_falls_back_to_the_default_font_when_nothing_is_stored(qapp, isolated_paths, monkeypatch):
	_fake_font_resource(monkeypatch)

	dlg = Preferences(None)

	assert dlg.chosenFont.family() == "Fira Code NF"
	assert dlg.chosenFont.pointSize() == 11
	assert dlg.chosenFontSize == 11


# --- export_settings_btn / import_settings_btn ------------------------------


def test_export_settings_btn_writes_settings_to_the_chosen_file(qapp, isolated_paths, tmp_path, monkeypatch):
	export_path = str(tmp_path / "exported.ini")
	monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *args, **kwargs: (export_path, "")))
	StoredSettings.CHOSEN_BOARD.set("Arduino UNO R3")
	dlg = Preferences(None)

	dlg.export_settings_btn()

	exported = QSettings(export_path, QSettings.Format.IniFormat)
	assert exported.value(StoredSettings.CHOSEN_BOARD.value) == "Arduino UNO R3"


def test_export_settings_btn_does_nothing_when_dialog_is_cancelled(qapp, isolated_paths, monkeypatch):
	monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *args, **kwargs: ("", "")))
	calls = []
	monkeypatch.setattr(StoredSettings, "export_settings", staticmethod(calls.append))
	dlg = Preferences(None)

	dlg.export_settings_btn()

	assert calls == []


def test_import_settings_btn_imports_from_the_chosen_file(qapp, isolated_paths, tmp_path, monkeypatch):
	import_path = str(tmp_path / "to_import.ini")
	source = QSettings(import_path, QSettings.Format.IniFormat)
	source.setValue(StoredSettings.CHOSEN_BOARD.value, "ImportedBoard")
	source.sync()
	monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *args, **kwargs: (import_path, "")))
	monkeypatch.setattr(
		QMessageBox, "question", staticmethod(lambda *args, **kwargs: QMessageBox.StandardButton.No)
	)
	dlg = Preferences(None)

	dlg.import_settings_btn()

	assert StoredSettings.CHOSEN_BOARD.get() == "ImportedBoard"


def test_import_settings_btn_does_nothing_when_dialog_is_cancelled(qapp, isolated_paths, monkeypatch):
	monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *args, **kwargs: ("", "")))
	calls = []
	monkeypatch.setattr(StoredSettings, "import_settings", staticmethod(calls.append))
	dlg = Preferences(None)

	dlg.import_settings_btn()

	assert calls == []


def test_import_settings_btn_reloads_the_app_when_the_user_confirms(qapp, isolated_paths, tmp_path, monkeypatch):
	import_path = str(tmp_path / "to_import.ini")
	QSettings(import_path, QSettings.Format.IniFormat).sync()
	monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *args, **kwargs: (import_path, "")))
	monkeypatch.setattr(
		QMessageBox, "question", staticmethod(lambda *args, **kwargs: QMessageBox.StandardButton.Yes)
	)
	reload_calls = []
	monkeypatch.setattr(preferences, "reload_app", lambda: reload_calls.append(True))
	dlg = Preferences(None)

	dlg.import_settings_btn()

	assert reload_calls == [True]


def test_import_settings_btn_does_not_reload_when_the_user_declines(qapp, isolated_paths, tmp_path, monkeypatch):
	import_path = str(tmp_path / "to_import.ini")
	QSettings(import_path, QSettings.Format.IniFormat).sync()
	monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *args, **kwargs: (import_path, "")))
	monkeypatch.setattr(
		QMessageBox, "question", staticmethod(lambda *args, **kwargs: QMessageBox.StandardButton.No)
	)
	reload_calls = []
	monkeypatch.setattr(preferences, "reload_app", lambda: reload_calls.append(True))
	dlg = Preferences(None)

	dlg.import_settings_btn()

	assert reload_calls == []


def test_import_settings_btn_refreshes_the_dialog_instead_of_reloading_when_declined(
	qapp, isolated_paths, tmp_path, monkeypatch
):
	_fake_font_resource(monkeypatch)
	import_path = str(tmp_path / "to_import.ini")
	source = QSettings(import_path, QSettings.Format.IniFormat)
	source.setValue(StoredSettings.APP_FONT_SIZE.value, 30)
	source.sync()
	monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *args, **kwargs: (import_path, "")))
	monkeypatch.setattr(
		QMessageBox, "question", staticmethod(lambda *args, **kwargs: QMessageBox.StandardButton.No)
	)
	dlg = Preferences(None)

	dlg.import_settings_btn()

	assert dlg.chosenFontSize == 30
	assert dlg.fontSizeBox.value() == 30


def test_import_settings_btn_does_not_prompt_to_reload_when_dialog_is_cancelled(qapp, isolated_paths, monkeypatch):
	monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *args, **kwargs: ("", "")))
	question_calls = []
	monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *args, **kwargs: question_calls.append(True)))
	dlg = Preferences(None)

	dlg.import_settings_btn()

	assert question_calls == []


# --- reset_to_defaults_btn ---------------------------------------------------


def test_reset_to_defaults_btn_clears_the_font_override_when_confirmed(qapp, isolated_paths, monkeypatch):
	_fake_font_resource(monkeypatch)
	monkeypatch.setattr(
		QMessageBox, "critical", staticmethod(lambda *args, **kwargs: QMessageBox.StandardButton.Yes)
	)
	StoredSettings.APP_FONT.set(QFont("Consolas", 20))
	StoredSettings.APP_FONT_SIZE.set(20)
	dlg = Preferences(None)
	assert dlg.chosenFont.family() == "Consolas"  # sanity: override applied on init
	assert dlg.chosenFontSize == 20

	dlg.reset_to_defaults_btn()

	assert StoredSettings.APP_FONT.get() is None
	assert StoredSettings.APP_FONT_SIZE.get() is None
	assert dlg.chosenFont.family() == "Fira Code NF"
	assert dlg.chosenFontSize == 11


def test_reset_to_defaults_btn_does_nothing_when_cancelled(qapp, isolated_paths, monkeypatch):
	_fake_font_resource(monkeypatch)
	monkeypatch.setattr(
		QMessageBox, "critical", staticmethod(lambda *args, **kwargs: QMessageBox.StandardButton.Cancel)
	)
	StoredSettings.APP_FONT.set(QFont("Consolas", 20))
	dlg = Preferences(None)

	dlg.reset_to_defaults_btn()

	stored = StoredSettings.APP_FONT.get()
	assert stored.family() == "Consolas"


def test_reset_to_defaults_btn_does_not_touch_settings_outside_the_preferences_group(
	qapp, isolated_paths, monkeypatch
):
	monkeypatch.setattr(
		QMessageBox, "critical", staticmethod(lambda *args, **kwargs: QMessageBox.StandardButton.Yes)
	)
	StoredSettings.CHOSEN_BOARD.set("Arduino UNO R3")
	dlg = Preferences(None)

	dlg.reset_to_defaults_btn()

	assert StoredSettings.CHOSEN_BOARD.get() == "Arduino UNO R3"
