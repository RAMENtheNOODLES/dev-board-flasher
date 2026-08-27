import pytest
from canlib.frame import Frame
from PySide6.QtCore import QModelIndex

from can_logging import CanLogging
from tools.j1939_dm1 import Dm1Message, Dm2Message, Dtc, Lamp, LampStatus

pytestmark = pytest.mark.integration


def _make_frame(msg_id, timestamp=1000):
	return Frame(id_=msg_id, data=bytes([1] * 8), dlc=8, timestamp=timestamp)


def _make_dm1(source_address=0x17, dtcs=()):
	off = Lamp(status="Off", flash="Slow Flash")
	return Dm1Message(
		source_address=source_address,
		lamp_status=LampStatus(malfunction_indicator=off, red_stop=off, amber_warning=off, protect=off),
		dtcs=tuple(dtcs),
	)


def _make_dm2(source_address=0x17, dtcs=()):
	off = Lamp(status="Off", flash="Slow Flash")
	return Dm2Message(
		source_address=source_address,
		lamp_status=LampStatus(malfunction_indicator=off, red_stop=off, amber_warning=off, protect=off),
		dtcs=tuple(dtcs),
	)


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


def test_populate_tree_labels_dbc_known_rows_with_id_and_name(qapp):
	view = CanLogging(None)

	view.populate_tree({0x100: ("EngineData", [])})

	node = view.nodes[0x100]
	assert node.text() == "0x100 - EngineData"


def test_update_tree_unhides_and_builds_children_on_first_receipt(qapp):
	view = CanLogging(None)
	view.populate_tree({0x100: ("EngineData", [("EngineSpeed", "rpm"), ("CoolantTemp", "C")])})
	node = view.nodes[0x100]

	view.update_tree(_make_frame(0x100), channel=0, decoded={"EngineSpeed": 1500.0})

	assert view.isRowHidden(node.row(), QModelIndex()) is False
	# Row 0 is the fake "VALUE/UNIT" sub-header; real signals start at row 1.
	assert node.rowCount() == 3
	assert node.child(0, 7).text() == "VALUE"
	assert node.child(0, 8).text() == "UNIT"
	assert node.child(1, 0).text() == "EngineSpeed"
	assert node.child(1, 7).text() == "1500.0"
	assert node.child(1, 8).text() == "rpm"
	assert node.child(2, 0).text() == "CoolantTemp"


def test_update_tree_does_not_duplicate_children_on_second_receipt(qapp):
	view = CanLogging(None)
	view.populate_tree({0x100: ("EngineData", [("EngineSpeed", "rpm")])})
	node = view.nodes[0x100]

	view.update_tree(_make_frame(0x100), channel=0, decoded={"EngineSpeed": 1500.0})
	view.update_tree(_make_frame(0x100), channel=0, decoded={"EngineSpeed": 1600.0})

	assert node.rowCount() == 2  # header + 1 signal, still - not re-added
	assert node.child(1, 7).text() == "1600.0"


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
	assert view.mainModel.item(row, 1).text() == "RX"  # DIR
	assert view.mainModel.item(row, 2).text() == "2"  # CHANNEL
	assert view.mainModel.item(row, 3).text() == "8"  # DLC
	assert view.mainModel.item(row, 4).text() == "01 01 01 01 01 01 01 01"  # DATA
	assert view.mainModel.item(row, 5).text() == "1234 ms"  # TIME


def test_update_tree_marks_a_sent_frame_with_tx_direction(qapp):
	view = CanLogging(None)
	view.populate_tree({0x100: ("EngineData", [])})

	view.update_tree(_make_frame(0x100), channel=0, direction="TX")

	row = view.nodes[0x100].row()
	assert view.mainModel.item(row, 1).text() == "TX"


def test_update_tree_direction_reflects_the_most_recent_update(qapp):
	view = CanLogging(None)
	view.populate_tree({0x100: ("EngineData", [])})

	view.update_tree(_make_frame(0x100), channel=0, direction="TX")
	view.update_tree(_make_frame(0x100), channel=0, direction="RX")

	row = view.nodes[0x100].row()
	assert view.mainModel.item(row, 1).text() == "RX"


def test_update_dm1_creates_a_row_with_lamp_and_dtc_children(qapp):
	view = CanLogging(None)
	dm1 = _make_dm1(source_address=0x17, dtcs=[Dtc(spn=1234, fmi=3, occurrence_count=5, spn_conversion_method=1)])

	view.update_dm1(dm1, channel=1, timestamp=1000)

	node = view.nodes[(1 << 29) | 0x17]
	assert node.text() == "J1939 DM1 - SA 0x17"
	assert view.isRowHidden(node.row(), QModelIndex()) is False
	# header + 4 lamps + header + 1 DTC
	assert node.rowCount() == 7
	assert node.child(1, 0).text() == "Malfunction Indicator Lamp"
	assert node.child(1, 7).text() == "Off"
	dtc_row = node.child(6, 0)
	assert dtc_row.text() == "SPN 1234 FMI 3"
	assert node.child(6, 7).text() == "5"
	assert node.child(6, 8).text() == "1"


def test_update_dm1_shows_no_active_dtcs_when_there_are_none(qapp):
	view = CanLogging(None)

	view.update_dm1(_make_dm1(dtcs=[]), channel=0, timestamp=1000)

	node = view.nodes[(1 << 29) | 0x17]
	assert node.child(5, 0).text() == "No active DTCs"


def test_update_dm1_rebuilds_children_when_the_dtc_list_changes(qapp):
	view = CanLogging(None)
	view.update_dm1(_make_dm1(dtcs=[Dtc(spn=1, fmi=1, occurrence_count=1, spn_conversion_method=0)]), channel=0, timestamp=1000)

	view.update_dm1(_make_dm1(dtcs=[]), channel=0, timestamp=2000)

	node = view.nodes[(1 << 29) | 0x17]
	assert node.child(5, 0).text() == "No active DTCs"
	assert node.rowCount() == 6


def test_update_dm1_includes_the_spn_name_when_a_lookup_is_set(qapp):
	view = CanLogging(None)
	view.set_spn_names({1234: "Engine Oil Pressure"})
	dm1 = _make_dm1(dtcs=[Dtc(spn=1234, fmi=3, occurrence_count=5, spn_conversion_method=1)])

	view.update_dm1(dm1, channel=0, timestamp=1000)

	node = view.nodes[(1 << 29) | 0x17]
	assert node.child(6, 0).text() == "SPN 1234 (Engine Oil Pressure) FMI 3"


def test_update_dm1_includes_both_spn_and_fmi_names_when_both_lookups_are_set(qapp):
	view = CanLogging(None)
	view.set_spn_names({1234: "Engine Oil Pressure"})
	view.set_fmi_names({3: "Voltage Above Normal"})
	dm1 = _make_dm1(dtcs=[Dtc(spn=1234, fmi=3, occurrence_count=5, spn_conversion_method=1)])

	view.update_dm1(dm1, channel=0, timestamp=1000)

	node = view.nodes[(1 << 29) | 0x17]
	assert node.child(6, 0).text() == "SPN 1234 (Engine Oil Pressure) FMI 3 (Voltage Above Normal)"


def test_update_dm1_shows_bare_spn_when_no_lookup_is_set(qapp):
	view = CanLogging(None)
	dm1 = _make_dm1(dtcs=[Dtc(spn=1234, fmi=3, occurrence_count=5, spn_conversion_method=1)])

	view.update_dm1(dm1, channel=0, timestamp=1000)

	node = view.nodes[(1 << 29) | 0x17]
	assert node.child(6, 0).text() == "SPN 1234 FMI 3"


def test_update_dm1_computes_delta_between_updates_for_the_same_source_address(qapp):
	view = CanLogging(None)
	view.update_dm1(_make_dm1(), channel=0, timestamp=1000)

	view.update_dm1(_make_dm1(), channel=0, timestamp=1250)

	row = view.nodes[(1 << 29) | 0x17].row()
	assert view.mainModel.item(row, 6).text() == "250 ms"


def test_update_dm1_always_shows_rx_direction(qapp):
	view = CanLogging(None)

	view.update_dm1(_make_dm1(), channel=0, timestamp=1000)

	row = view.nodes[(1 << 29) | 0x17].row()
	assert view.mainModel.item(row, 1).text() == "RX"


def test_update_dm2_creates_a_row_with_lamp_and_dtc_children(qapp):
	view = CanLogging(None)
	dm2 = _make_dm2(source_address=0x17, dtcs=[Dtc(spn=1234, fmi=3, occurrence_count=5, spn_conversion_method=1)])

	view.update_dm2(dm2, channel=1, timestamp=1000)

	node = view.nodes[(1 << 30) | 0x17]
	assert node.text() == "J1939 DM2 - SA 0x17"
	assert view.isRowHidden(node.row(), QModelIndex()) is False
	dtc_row = node.child(6, 0)
	assert dtc_row.text() == "SPN 1234 FMI 3"


def test_update_dm2_shows_no_previously_active_dtcs_when_there_are_none(qapp):
	view = CanLogging(None)

	view.update_dm2(_make_dm2(dtcs=[]), channel=0, timestamp=1000)

	node = view.nodes[(1 << 30) | 0x17]
	assert node.child(5, 0).text() == "No previously active DTCs"


def test_update_dm1_and_update_dm2_dont_collide_for_the_same_source_address(qapp):
	view = CanLogging(None)

	view.update_dm1(_make_dm1(source_address=0x17, dtcs=[]), channel=0, timestamp=1000)
	view.update_dm2(_make_dm2(source_address=0x17, dtcs=[]), channel=0, timestamp=1000)

	dm1_node = view.nodes[(1 << 29) | 0x17]
	dm2_node = view.nodes[(1 << 30) | 0x17]
	assert dm1_node is not dm2_node
	assert dm1_node.text() == "J1939 DM1 - SA 0x17"
	assert dm2_node.text() == "J1939 DM2 - SA 0x17"
