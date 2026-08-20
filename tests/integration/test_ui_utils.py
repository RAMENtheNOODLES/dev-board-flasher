import pytest
from PySide6.QtGui import QFont, QFontDatabase

from utils.ui_utils import get_global_font
from utils.wiz_utils.stored_settings import StoredSettings

pytestmark = pytest.mark.integration


def _fake_font_resource(monkeypatch, family="Fira Code NF"):
	monkeypatch.setattr(QFontDatabase, "addApplicationFont", staticmethod(lambda path: 0))
	monkeypatch.setattr(QFontDatabase, "applicationFontFamilies", staticmethod(lambda font_id: [family]))


def test_returns_none_when_the_font_resource_fails_to_load(qapp, monkeypatch):
	monkeypatch.setattr(QFontDatabase, "addApplicationFont", staticmethod(lambda path: -1))

	assert get_global_font() is None


def test_returns_the_default_font_when_nothing_is_stored(qapp, isolated_paths, monkeypatch):
	_fake_font_resource(monkeypatch)

	font = get_global_font()

	assert font.family() == "Fira Code NF"
	assert font.pointSize() == 11


def test_returns_the_stored_font_family_override_when_set(qapp, isolated_paths, monkeypatch):
	_fake_font_resource(monkeypatch)
	StoredSettings.APP_FONT.set(QFont("Consolas", 99))  # size on the stored QFont itself is ignored

	font = get_global_font()

	assert font.family() == "Consolas"
	assert font.pointSize() == 11


def test_returns_the_stored_font_size_override_when_set(qapp, isolated_paths, monkeypatch):
	_fake_font_resource(monkeypatch)
	StoredSettings.APP_FONT_SIZE.set(20)

	font = get_global_font()

	assert font.family() == "Fira Code NF"
	assert font.pointSize() == 20


def test_returns_both_stored_overrides_when_both_are_set(qapp, isolated_paths, monkeypatch):
	_fake_font_resource(monkeypatch)
	StoredSettings.APP_FONT.set(QFont("Consolas", 8))
	StoredSettings.APP_FONT_SIZE.set(20)

	font = get_global_font()

	assert font.family() == "Consolas"
	assert font.pointSize() == 20
