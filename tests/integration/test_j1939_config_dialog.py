import pytest
from PySide6.QtWidgets import QDialog, QFileDialog, QMessageBox

from j1939_config_dialog import J1939ConfigDialog
from utils.wiz_utils.stored_settings import StoredSettings

pytestmark = pytest.mark.integration


def test_init_prefills_fields_from_previously_persisted_paths(qapp, isolated_paths):
	StoredSettings.CAN_DM1_SPN_FILE.set("C:/spns.csv")
	StoredSettings.CAN_DM1_FMI_FILE.set("C:/fmis.csv")

	dlg = J1939ConfigDialog(None)

	assert dlg.ui.dM1SPNLineEdit.text() == "C:/spns.csv"
	assert dlg.ui.dM1FMILineEdit.text() == "C:/fmis.csv"


def test_init_leaves_fields_blank_when_nothing_is_persisted(qapp, isolated_paths):
	dlg = J1939ConfigDialog(None)

	assert dlg.ui.dM1SPNLineEdit.text() == ""
	assert dlg.ui.dM1FMILineEdit.text() == ""


def test_browse_spn_file_fills_in_the_chosen_path(qapp, isolated_paths, monkeypatch):
	monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: ("C:/chosen_spns.csv", "")))
	dlg = J1939ConfigDialog(None)

	dlg._browse_spn_file()

	assert dlg.ui.dM1SPNLineEdit.text() == "C:/chosen_spns.csv"


def test_browse_spn_file_does_nothing_when_cancelled(qapp, isolated_paths, monkeypatch):
	monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: ("", "")))
	dlg = J1939ConfigDialog(None)
	dlg.ui.dM1SPNLineEdit.setText("C:/existing.csv")

	dlg._browse_spn_file()

	assert dlg.ui.dM1SPNLineEdit.text() == "C:/existing.csv"


def test_browse_fmi_file_fills_in_the_chosen_path(qapp, isolated_paths, monkeypatch):
	monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: ("C:/chosen_fmis.csv", "")))
	dlg = J1939ConfigDialog(None)

	dlg._browse_fmi_file()

	assert dlg.ui.dM1FMILineEdit.text() == "C:/chosen_fmis.csv"


def test_accept_loads_both_files_and_persists_their_paths(qapp, isolated_paths, tmp_path):
	spn_path = tmp_path / "spns.csv"
	spn_path.write_text("spn,name\n100,Engine Oil Pressure\n", encoding="utf-8")
	fmi_path = tmp_path / "fmis.csv"
	fmi_path.write_text("fmi,name\n3,Voltage Above Normal\n", encoding="utf-8")

	dlg = J1939ConfigDialog(None)
	dlg.ui.dM1SPNLineEdit.setText(str(spn_path))
	dlg.ui.dM1FMILineEdit.setText(str(fmi_path))

	dlg.accept()

	assert dlg.spn_names == {100: "Engine Oil Pressure"}
	assert dlg.fmi_names == {3: "Voltage Above Normal"}
	assert dlg.result() == QDialog.DialogCode.Accepted
	assert StoredSettings.CAN_DM1_SPN_FILE.get(None) == str(spn_path)
	assert StoredSettings.CAN_DM1_FMI_FILE.get(None) == str(fmi_path)


def test_accept_with_both_fields_blank_succeeds_with_empty_lookups(qapp, isolated_paths):
	dlg = J1939ConfigDialog(None)

	dlg.accept()

	assert dlg.spn_names == {}
	assert dlg.fmi_names == {}
	assert dlg.result() == QDialog.DialogCode.Accepted


def test_accept_shows_an_error_and_stays_open_when_the_spn_file_is_missing(qapp, isolated_paths, monkeypatch):
	shown = []
	monkeypatch.setattr(QMessageBox, "critical", staticmethod(lambda *a, **k: shown.append(a)))
	dlg = J1939ConfigDialog(None)
	dlg.ui.dM1SPNLineEdit.setText("C:/does/not/exist.csv")

	dlg.accept()

	assert len(shown) == 1
	assert dlg.result() != QDialog.DialogCode.Accepted
	assert dlg.spn_names == {}


def test_accept_does_not_persist_a_partially_valid_pair_when_the_other_field_fails(
	qapp, isolated_paths, tmp_path, monkeypatch
):
	monkeypatch.setattr(QMessageBox, "critical", staticmethod(lambda *a, **k: None))
	spn_path = tmp_path / "spns.csv"
	spn_path.write_text("spn,name\n100,Engine Oil Pressure\n", encoding="utf-8")
	dlg = J1939ConfigDialog(None)
	dlg.ui.dM1SPNLineEdit.setText(str(spn_path))
	dlg.ui.dM1FMILineEdit.setText("C:/does/not/exist.csv")

	dlg.accept()

	assert StoredSettings.CAN_DM1_SPN_FILE.get(None) is None
	assert StoredSettings.CAN_DM1_FMI_FILE.get(None) is None
