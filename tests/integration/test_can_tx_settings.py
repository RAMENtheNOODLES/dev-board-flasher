import pytest
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QMessageBox

from can_tx_settings import TxSettingsDialog
from tools.can import TxMessageConfig, TxMessageInfo, TxSignalInfo
from utils.wiz_utils.tx_scheduler import TxScheduler

pytestmark = pytest.mark.integration


class _FakeCan:
	def __init__(self, messages):
		self._messages = messages

	def dbc_tx_messages(self):
		return self._messages


_ENGINE_TEMP = TxMessageInfo(
	name="EngineTemp1",
	pgn=0xFEEE,
	signals=(
		TxSignalInfo(name="CoolantTemp", unit="C", default_value=-40.0),
		TxSignalInfo(name="OilTemp", unit="C", default_value=-40.0),
	),
)
_ENGINE_SPEED = TxMessageInfo(
	name="EngineSpeed1", pgn=0xF004, signals=(TxSignalInfo(name="RPM", unit="rpm", default_value=0.0),)
)
_FAN_CONTROL = TxMessageInfo(
	name="FanControl1",
	pgn=0xFDA0,
	signals=(
		TxSignalInfo(
			name="FanStatus", unit="", default_value=0.0, enum_values={"Off": 0, "On": 1, "Error": 2}
		),
	),
)


def test_init_builds_no_rows_when_the_scheduler_has_no_configs(qapp, isolated_paths):
	dlg = TxSettingsDialog(_FakeCan([_ENGINE_TEMP]), TxScheduler(), None)

	assert dlg.ui.txMessages.rowCount() == 0


def test_init_prefills_a_row_per_existing_scheduler_config(qapp, isolated_paths):
	scheduler = TxScheduler()
	scheduler.set_configs([
		TxMessageConfig(message_name="EngineSpeed1", rate_ms=250, enabled=True, signal_values={"RPM": 1500.0})
	])

	dlg = TxSettingsDialog(_FakeCan([_ENGINE_TEMP, _ENGINE_SPEED]), scheduler, None)

	assert dlg.ui.txMessages.rowCount() == 1
	pgn_combo = dlg.ui.txMessages.cellWidget(0, 0)
	assert pgn_combo.currentData() == "EngineSpeed1"
	rate_spin = dlg.ui.txMessages.cellWidget(0, 1)
	assert rate_spin.value() == 250
	enabled_check = dlg.ui.txMessages.cellWidget(0, 2).findChild(QCheckBox)
	assert enabled_check.isChecked() is True
	signals_container = dlg.ui.txMessages.cellWidget(0, 3)
	assert signals_container.editors["RPM"].value() == 1500.0


def test_add_row_button_adds_a_row_defaulted_from_the_first_dbc_message(qapp, isolated_paths):
	dlg = TxSettingsDialog(_FakeCan([_ENGINE_TEMP, _ENGINE_SPEED]), TxScheduler(), None)

	dlg.ui.newTxButton.click()

	assert dlg.ui.txMessages.rowCount() == 1
	pgn_combo = dlg.ui.txMessages.cellWidget(0, 0)
	assert pgn_combo.currentData() == "EngineTemp1"
	signals_container = dlg.ui.txMessages.cellWidget(0, 3)
	assert signals_container.editors["CoolantTemp"].value() == -40.0
	assert signals_container.editors["OilTemp"].value() == -40.0
	enabled_check = dlg.ui.txMessages.cellWidget(0, 2).findChild(QCheckBox)
	assert enabled_check.isChecked() is False


def test_add_row_button_warns_and_adds_nothing_when_no_dbc_messages_are_available(qapp, isolated_paths, monkeypatch):
	shown = []
	monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: shown.append(a)))
	dlg = TxSettingsDialog(_FakeCan([]), TxScheduler(), None)

	dlg.ui.newTxButton.click()

	assert dlg.ui.txMessages.rowCount() == 0
	assert len(shown) == 1


def test_changing_the_pgn_combo_rebuilds_the_signal_editors(qapp, isolated_paths):
	dlg = TxSettingsDialog(_FakeCan([_ENGINE_TEMP, _ENGINE_SPEED]), TxScheduler(), None)
	dlg._add_row()
	pgn_combo = dlg.ui.txMessages.cellWidget(0, 0)

	pgn_combo.setCurrentIndex(pgn_combo.findData("EngineSpeed1"))

	signals_container = dlg.ui.txMessages.cellWidget(0, 3)
	assert list(signals_container.editors.keys()) == ["RPM"]


def test_a_signal_with_a_value_table_gets_a_combo_box_defaulted_to_its_matching_label(qapp, isolated_paths):
	dlg = TxSettingsDialog(_FakeCan([_FAN_CONTROL]), TxScheduler(), None)

	dlg._add_row()

	signals_container = dlg.ui.txMessages.cellWidget(0, 3)
	editor = signals_container.editors["FanStatus"]
	assert isinstance(editor, QComboBox)
	assert [editor.itemText(i) for i in range(editor.count())] == ["Off", "On", "Error"]
	assert editor.currentText() == "Off"
	assert editor.currentData() == 0


def test_a_plain_signal_still_gets_a_double_spin_box(qapp, isolated_paths):
	dlg = TxSettingsDialog(_FakeCan([_ENGINE_TEMP]), TxScheduler(), None)

	dlg._add_row()

	signals_container = dlg.ui.txMessages.cellWidget(0, 3)
	assert isinstance(signals_container.editors["CoolantTemp"], QDoubleSpinBox)


def test_init_prefills_a_combo_box_from_a_persisted_enum_value(qapp, isolated_paths):
	scheduler = TxScheduler()
	scheduler.set_configs([
		TxMessageConfig(message_name="FanControl1", rate_ms=100, enabled=True, signal_values={"FanStatus": 2.0})
	])

	dlg = TxSettingsDialog(_FakeCan([_FAN_CONTROL]), scheduler, None)

	signals_container = dlg.ui.txMessages.cellWidget(0, 3)
	assert signals_container.editors["FanStatus"].currentText() == "Error"


def test_accept_reads_the_selected_enum_labels_raw_value(qapp, isolated_paths):
	scheduler = TxScheduler()
	dlg = TxSettingsDialog(_FakeCan([_FAN_CONTROL]), scheduler, None)
	dlg._add_row()
	signals_container = dlg.ui.txMessages.cellWidget(0, 3)
	combo = signals_container.editors["FanStatus"]
	combo.setCurrentIndex(combo.findData(1))

	dlg.accept()

	configs = scheduler.get_configs()
	assert configs[0].signal_values == {"FanStatus": 1.0}


def test_adding_a_row_grows_the_window_to_fit_it(qapp, isolated_paths):
	# Width, not height: a single row's content is narrower than the
	# button column but shorter than the button column + button box, so
	# only width is guaranteed to grow from just one added row.
	dlg = TxSettingsDialog(_FakeCan([_ENGINE_TEMP]), TxScheduler(), None)
	empty_width = dlg.width()

	dlg._add_row()

	assert dlg.width() > empty_width


def test_window_size_is_capped_at_90_percent_of_the_available_screen(qapp, isolated_paths):
	dlg = TxSettingsDialog(_FakeCan([_ENGINE_TEMP, _ENGINE_SPEED, _FAN_CONTROL]), TxScheduler(), None)

	for _ in range(30):
		dlg._add_row()

	available = (dlg.screen() or QGuiApplication.primaryScreen()).availableGeometry()
	assert dlg.width() <= round(available.width() * 0.9)
	assert dlg.height() <= round(available.height() * 0.9)


def test_removing_every_row_shrinks_the_window_back_down(qapp, isolated_paths):
	dlg = TxSettingsDialog(_FakeCan([_ENGINE_TEMP]), TxScheduler(), None)
	empty_size = dlg.size()
	# Enough rows that the table's content height exceeds the button
	# column/box's own minimum height, so the window is guaranteed to have
	# actually grown before checking that removing them shrinks it back.
	for _ in range(8):
		dlg._add_row()
	assert dlg.height() > empty_size.height()

	while dlg.ui.txMessages.rowCount() > 0:
		dlg.ui.txMessages.selectRow(0)
		dlg._remove_selected_rows()

	assert dlg.size() == empty_size


def test_remove_selected_rows_removes_only_the_selected_row(qapp, isolated_paths):
	dlg = TxSettingsDialog(_FakeCan([_ENGINE_TEMP, _ENGINE_SPEED]), TxScheduler(), None)
	dlg._add_row()
	dlg._add_row()
	dlg.ui.txMessages.selectRow(0)

	dlg._remove_selected_rows()

	assert dlg.ui.txMessages.rowCount() == 1


def test_accept_applies_the_table_to_the_scheduler_and_closes_the_dialog(qapp, isolated_paths):
	scheduler = TxScheduler()
	dlg = TxSettingsDialog(_FakeCan([_ENGINE_TEMP, _ENGINE_SPEED]), scheduler, None)
	dlg._add_row()
	rate_spin = dlg.ui.txMessages.cellWidget(0, 1)
	rate_spin.setValue(500)
	enabled_check = dlg.ui.txMessages.cellWidget(0, 2).findChild(QCheckBox)
	enabled_check.setChecked(True)

	dlg.accept()

	assert dlg.result() == QDialog.DialogCode.Accepted
	configs = scheduler.get_configs()
	assert len(configs) == 1
	assert configs[0] == TxMessageConfig(
		message_name="EngineTemp1", rate_ms=500, enabled=True,
		signal_values={"CoolantTemp": -40.0, "OilTemp": -40.0},
	)


def test_accept_after_removing_every_row_applies_an_empty_config_list(qapp, isolated_paths):
	scheduler = TxScheduler()
	scheduler.set_configs([
		TxMessageConfig(
			message_name="EngineTemp1", rate_ms=100, enabled=True,
			signal_values={"CoolantTemp": -40.0, "OilTemp": -40.0},
		)
	])
	dlg = TxSettingsDialog(_FakeCan([_ENGINE_TEMP]), scheduler, None)
	dlg.ui.txMessages.selectRow(0)
	dlg._remove_selected_rows()

	dlg.accept()

	assert scheduler.get_configs() == []
