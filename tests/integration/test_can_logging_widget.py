import pytest
from canlib.frame import Frame
from PySide6.QtCore import QModelIndex

from can_logging import CanLogging

pytestmark = pytest.mark.integration


def _make_frame(msg_id, timestamp=1000):
	return Frame(id_=msg_id, data=bytes([1] * 8), dlc=8, timestamp=timestamp)


def test_populate_tree_creates_hidden_childless_rows_for_each_dbc_message(qapp):
	view = CanLogging(None)
	dbc_data = {
		0x100: ("EngineData", [("EngineSpeed", "rpm")]),
		0x200: ("BrakeData", [("BrakePressure", "kPa")]),
	}

	view.populate_tree(dbc_data)

	for msg_id in dbc_data:
		node = view.nodes[msg_id]
		# Signal children (including the fake sub-header row) are only
		# built lazily in update_tree(), on first receipt.
		assert node.rowCount() == 0
		assert view.isRowHidden(node.row(), QModelIndex())


def test_update_tree_unhides_and_builds_children_on_first_receipt(qapp):
	view = CanLogging(None)
	view.populate_tree({0x100: ("EngineData", [("EngineSpeed", "rpm"), ("CoolantTemp", "C")])})
	node = view.nodes[0x100]

	view.update_tree(_make_frame(0x100), channel=0, decoded={"EngineSpeed": 1500.0})

	assert view.isRowHidden(node.row(), QModelIndex()) is False
	# Row 0 is the fake "VALUE/UNIT" sub-header; real signals start at row 1.
	assert node.rowCount() == 3
	assert node.child(0, 6).text() == "VALUE"
	assert node.child(0, 7).text() == "UNIT"
	assert node.child(1, 0).text() == "EngineSpeed"
	assert node.child(1, 6).text() == "1500.0"
	assert node.child(1, 7).text() == "rpm"
	assert node.child(2, 0).text() == "CoolantTemp"


def test_update_tree_does_not_duplicate_children_on_second_receipt(qapp):
	view = CanLogging(None)
	view.populate_tree({0x100: ("EngineData", [("EngineSpeed", "rpm")])})
	node = view.nodes[0x100]

	view.update_tree(_make_frame(0x100), channel=0, decoded={"EngineSpeed": 1500.0})
	view.update_tree(_make_frame(0x100), channel=0, decoded={"EngineSpeed": 1600.0})

	assert node.rowCount() == 2  # header + 1 signal, still - not re-added
	assert node.child(1, 6).text() == "1600.0"


def test_update_tree_adds_unknown_ids_above_dbc_known_messages(qapp):
	view = CanLogging(None)
	view.populate_tree({0x100: ("EngineData", [])})

	view.update_tree(_make_frame(0x999), channel=0)

	unknown_node = view.nodes[0x999]
	known_node = view.nodes[0x100]
	assert unknown_node.text() == "0x999"
	assert unknown_node.row() < known_node.row()
	assert view.isRowHidden(unknown_node.row(), QModelIndex()) is False


def test_populate_tree_clears_previous_rows_on_reconnect(qapp):
	view = CanLogging(None)
	view.populate_tree({0x100: ("EngineData", [])})
	view.update_tree(_make_frame(0x999), channel=0)
	assert view.mainModel.rowCount() == 2  # 1 known + 1 unknown

	# Simulate a reconnect: populate_tree runs again with the same DBC.
	view.populate_tree({0x100: ("EngineData", [])})

	assert view.mainModel.rowCount() == 1
	assert view.mainModel.rowCount() == len(view.nodes)


def test_a_dbc_message_with_zero_signals_still_becomes_visible_when_received(qapp):
	view = CanLogging(None)
	view.populate_tree({0x300: ("NoSignals", [])})
	node = view.nodes[0x300]

	view.update_tree(_make_frame(0x300), channel=0, decoded={})

	assert view.isRowHidden(node.row(), QModelIndex()) is False
	assert node.rowCount() == 1  # just the fake sub-header, no real signals


def test_update_tree_fills_in_message_row_columns(qapp):
	view = CanLogging(None)
	view.populate_tree({0x100: ("EngineData", [])})

	view.update_tree(_make_frame(0x100, timestamp=1234), channel=2)

	row = view.nodes[0x100].row()
	assert view.mainModel.item(row, 1).text() == "2"  # CHANNEL
	assert view.mainModel.item(row, 2).text() == "8"  # DLC
	assert view.mainModel.item(row, 3).text() == "01 01 01 01 01 01 01 01"  # DATA
	assert view.mainModel.item(row, 4).text() == "1234 ms"  # TIME
