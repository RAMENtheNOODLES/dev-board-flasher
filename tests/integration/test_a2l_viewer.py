import pytest
from pya2l.parser import A2lError
from pya2l.protobuf.A2L_pb2 import (
	AxisPtsType,
	CharacteristicType,
	CompuMethodType,
	FunctionType,
	GroupType,
	MeasurementType,
	RecordLayoutType,
	RootNodeType,
	UnitType,
)
from PySide6.QtWidgets import QFileDialog, QMessageBox

import a2l_viewer
from a2l_viewer import (
	A2LViewer,
	_pad_short_matrix_dims,
	_quote_bare_format_specs,
	_strip_if_data_blocks,
)
from utils.wiz_utils.stored_settings import StoredSettings

pytestmark = pytest.mark.integration


# --- _strip_if_data_blocks ---------------------------------------------------


def test_strip_if_data_blocks_removes_a_single_block():
	data = b'/begin MODULE m ""\n/begin IF_DATA CCP\nRAM\n/end IF_DATA\n/end MODULE'

	assert _strip_if_data_blocks(data) == b'/begin MODULE m ""\n\n/end MODULE'


def test_strip_if_data_blocks_tracks_nested_begin_end_pairs():
	"""Regression test.

	Real IF_DATA content (e.g. a CCP TP_BLOB) nests further /begin.../end
	sub-blocks - the first `/end` seen isn't necessarily the one that closes
	the IF_DATA block itself, so a naive "up to the next /end" search would
	truncate the removal partway through and corrupt the rest of the file.
	"""
	data = (
		b"/begin IF_DATA CCP\n"
		b"/begin TP_BLOB\n"
		b"/begin DEFINED_PAGES\n"
		b"RAM\n"
		b"/end DEFINED_PAGES\n"
		b"/end TP_BLOB\n"
		b"/end IF_DATA\n"
		b"KEEP_ME"
	)

	assert _strip_if_data_blocks(data) == b"\nKEEP_ME"


def test_strip_if_data_blocks_removes_multiple_sibling_blocks():
	data = b"A /begin IF_DATA X\n1\n/end IF_DATA B /begin IF_DATA Y\n2\n/end IF_DATA C"

	assert _strip_if_data_blocks(data) == b"A  B  C"


def test_strip_if_data_blocks_ignores_lookalike_text_inside_a_quoted_string():
	data = b'/begin MODULE m "contains /begin IF_DATA text" /end MODULE'

	assert _strip_if_data_blocks(data) == data


def test_strip_if_data_blocks_is_a_no_op_without_any_if_data():
	data = b'/begin MODULE m "" /end MODULE'

	assert _strip_if_data_blocks(data) == data


# --- _quote_bare_format_specs -------------------------------------------------


def test_quote_bare_format_specs_wraps_an_unquoted_spec_in_quotes():
	data = b"FORMAT %12.3"

	assert _quote_bare_format_specs(data) == b'FORMAT "%12.3"'


def test_quote_bare_format_specs_leaves_an_already_quoted_spec_untouched():
	data = b'FORMAT "%12.3"'

	assert _quote_bare_format_specs(data) == data


def test_quote_bare_format_specs_fixes_every_occurrence_in_the_file():
	data = b"FORMAT %6.2\nFORMAT %12.3\n"

	assert _quote_bare_format_specs(data) == b'FORMAT "%6.2"\nFORMAT "%12.3"\n'


def test_quote_bare_format_specs_is_a_no_op_without_any_format_field():
	data = b'/begin MODULE m "" /end MODULE'

	assert _quote_bare_format_specs(data) == data


# --- _pad_short_matrix_dims ---------------------------------------------------


def test_pad_short_matrix_dims_pads_a_single_dimension_to_three():
	data = b"MATRIX_DIM 16"

	assert _pad_short_matrix_dims(data) == b"MATRIX_DIM 16 0 0"


def test_pad_short_matrix_dims_pads_two_dimensions_to_three():
	data = b"MATRIX_DIM 16 4"

	assert _pad_short_matrix_dims(data) == b"MATRIX_DIM 16 4 0"


def test_pad_short_matrix_dims_leaves_a_full_three_dimensions_untouched():
	data = b"MATRIX_DIM 16 4 2"

	assert _pad_short_matrix_dims(data) == data


def test_pad_short_matrix_dims_accepts_hex_dimensions():
	data = b"MATRIX_DIM 0x10"

	assert _pad_short_matrix_dims(data) == b"MATRIX_DIM 0x10 0 0"


def test_pad_short_matrix_dims_fixes_every_occurrence_in_the_file():
	data = b"MATRIX_DIM 16\nMATRIX_DIM 8 2\n"

	assert _pad_short_matrix_dims(data) == b"MATRIX_DIM 16 0 0\nMATRIX_DIM 8 2 0\n"


def test_pad_short_matrix_dims_is_a_no_op_without_any_matrix_dim_field():
	data = b'/begin MODULE m "" /end MODULE'

	assert _pad_short_matrix_dims(data) == data


# --- row builders (pure functions of a protobuf message, no window needed) --


def test_measurement_row_reads_datatype_and_ecu_address():
	m = MeasurementType()
	m.Name.Value = "rpm"
	m.LongIdentifier.Value = "engine speed"
	m.DataType.Value = "UBYTE"
	m.ECU_ADDRESS.Address.Value = 0x1000

	assert A2LViewer._measurement_row(m) == ["rpm", "UBYTE", "0x1000", "engine speed"]


def test_measurement_row_leaves_address_blank_when_ecu_address_is_absent():
	m = MeasurementType()
	m.Name.Value = "rpm"

	assert A2LViewer._measurement_row(m) == ["rpm", "", "", ""]


def test_characteristic_row_reads_type_directly_since_it_is_not_wrapper_typed():
	c = CharacteristicType()
	c.Name.Value = "gain"
	c.LongIdentifier.Value = "gain factor"
	c.Type = "VALUE"
	c.Address.Value = 0x2000

	assert A2LViewer._characteristic_row(c) == ["gain", "VALUE", "0x2000", "gain factor"]


def test_characteristic_row_leaves_address_blank_when_absent():
	c = CharacteristicType()
	c.Name.Value = "gain"

	assert A2LViewer._characteristic_row(c)[2] == ""


def test_compu_method_row_builds_expected_columns():
	cm = CompuMethodType()
	cm.Name.Value = "conv_rpm"
	cm.LongIdentifier.Value = "rpm conversion"
	cm.ConversionType = "IDENTICAL"
	cm.Unit.Value = "rpm"

	assert A2LViewer._compu_method_row(cm) == ["conv_rpm", "IDENTICAL", "rpm", "rpm conversion"]


def test_function_row_builds_expected_columns():
	f = FunctionType()
	f.Name.Value = "idle_control"
	f.LongIdentifier.Value = "Idle Control Function"

	assert A2LViewer._function_row(f) == ["idle_control", "", "", "Idle Control Function"]


def test_group_row_uses_groupname_and_grouplongidentifier_not_name():
	g = GroupType()
	g.GroupName.Value = "Sensors"
	g.GroupLongIdentifier.Value = "All sensor signals"

	assert A2LViewer._group_row(g) == ["Sensors", "", "", "All sensor signals"]


def test_axis_pts_row_builds_expected_columns():
	a = AxisPtsType()
	a.Name.Value = "rpm_axis"
	a.LongIdentifier.Value = "RPM axis points"
	a.Address.Value = 0x3000

	assert A2LViewer._axis_pts_row(a) == ["rpm_axis", "", "0x3000", "RPM axis points"]


def test_record_layout_row_only_has_a_name():
	r = RecordLayoutType()
	r.Name.Value = "rl_std"

	assert A2LViewer._record_layout_row(r) == ["rl_std", "", "", ""]


def test_unit_row_builds_expected_columns():
	u = UnitType()
	u.Name.Value = "u_rpm"
	u.LongIdentifier.Value = "revolutions per minute"
	u.Type = "DERIVED"
	u.Display.Value = "rpm"

	assert A2LViewer._unit_row(u) == ["u_rpm", "DERIVED", "rpm", "revolutions per minute"]


# --- parse_file_btn ----------------------------------------------------------


class _FakeParser:
	"""Stands in for `A2lParser` as a context manager, without needing its real gRPC/DLL backend."""

	def __init__(self, tree=None, error=None):
		self._tree = tree
		self._error = error
		self.received_data = None

	def __enter__(self):
		return self

	def __exit__(self, *exc_info):
		return False

	def tree_from_a2l(self, data):
		self.received_data = data
		if self._error is not None:
			raise self._error
		return self._tree


def _patch_parser(monkeypatch, tree=None, error=None):
	fake = _FakeParser(tree, error)
	monkeypatch.setattr(a2l_viewer, "A2lParser", lambda *args, **kwargs: fake)
	return fake


def _build_tree(*module_names) -> RootNodeType:
	tree = RootNodeType()
	for name in module_names:
		tree.PROJECT.MODULE.add().Name.Value = name
	return tree


def _capture_critical(monkeypatch):
	calls = []
	monkeypatch.setattr(QMessageBox, "critical", staticmethod(lambda *args, **kwargs: calls.append(args)))
	return calls


def test_parse_file_btn_shows_an_error_when_the_file_does_not_exist(qapp, monkeypatch):
	viewer = A2LViewer(None)
	viewer.a2l_file = "does_not_exist.a2l"
	critical_calls = _capture_critical(monkeypatch)

	viewer.parse_file_btn()

	assert len(critical_calls) == 1
	assert viewer.a2lTree.topLevelItemCount() == 0


def test_parse_file_btn_shows_an_error_when_parsing_fails(qapp, monkeypatch, tmp_path):
	a2l_file = tmp_path / "bad.a2l"
	a2l_file.write_bytes(b"not a2l")
	viewer = A2LViewer(None)
	viewer.a2l_file = str(a2l_file)
	_patch_parser(monkeypatch, error = A2lError("mismatched input"))
	critical_calls = _capture_critical(monkeypatch)

	viewer.parse_file_btn()

	assert len(critical_calls) == 1
	assert "mismatched input" in critical_calls[0][2]
	assert viewer.a2lTree.topLevelItemCount() == 0


def test_parse_file_btn_strips_a_leading_utf8_bom_before_parsing(qapp, monkeypatch, tmp_path):
	"""Regression test.

	Files exported by common calibration tools (e.g. INCA, CANape) are often
	saved as UTF-8 with a BOM. pya2l's grammar doesn't skip it, producing a
	spurious "token recognition error at: ''" for line 1 alongside any real
	errors in the file - stripping it keeps that noise out of the reported
	error and lets the real content parse normally.
	"""
	a2l_file = tmp_path / "sample.a2l"
	a2l_file.write_bytes(b"\xef\xbb\xbfASAP2_VERSION 1 61\n")
	viewer = A2LViewer(None)
	viewer.a2l_file = str(a2l_file)
	fake_parser = _patch_parser(monkeypatch, tree = _build_tree("test_module"))

	viewer.parse_file_btn()

	assert fake_parser.received_data == b"ASAP2_VERSION 1 61\n"


def test_parse_file_btn_strips_if_data_blocks_before_parsing(qapp, monkeypatch, tmp_path):
	a2l_file = tmp_path / "sample.a2l"
	a2l_file.write_bytes(b'/begin MODULE m ""\n/begin IF_DATA CCP\nRAM\n/end IF_DATA\n/end MODULE\n')
	viewer = A2LViewer(None)
	viewer.a2l_file = str(a2l_file)
	fake_parser = _patch_parser(monkeypatch, tree = _build_tree("test_module"))

	viewer.parse_file_btn()

	assert b"IF_DATA" not in fake_parser.received_data
	assert b"RAM" not in fake_parser.received_data


def test_parse_file_btn_quotes_bare_format_specs_before_parsing(qapp, monkeypatch, tmp_path):
	a2l_file = tmp_path / "sample.a2l"
	a2l_file.write_bytes(b'/begin MODULE m ""\nFORMAT %12.3\n/end MODULE\n')
	viewer = A2LViewer(None)
	viewer.a2l_file = str(a2l_file)
	fake_parser = _patch_parser(monkeypatch, tree = _build_tree("test_module"))

	viewer.parse_file_btn()

	assert b'FORMAT "%12.3"' in fake_parser.received_data


def test_parse_file_btn_pads_short_matrix_dims_before_parsing(qapp, monkeypatch, tmp_path):
	a2l_file = tmp_path / "sample.a2l"
	a2l_file.write_bytes(b'/begin MODULE m ""\nMATRIX_DIM 16\n/end MODULE\n')
	viewer = A2LViewer(None)
	viewer.a2l_file = str(a2l_file)
	fake_parser = _patch_parser(monkeypatch, tree = _build_tree("test_module"))

	viewer.parse_file_btn()

	assert b"MATRIX_DIM 16 0 0" in fake_parser.received_data


def test_parse_file_btn_adds_one_top_level_item_per_module(qapp, monkeypatch, tmp_path):
	a2l_file = tmp_path / "sample.a2l"
	a2l_file.write_bytes(b"")
	viewer = A2LViewer(None)
	viewer.a2l_file = str(a2l_file)
	_patch_parser(monkeypatch, tree = _build_tree("engine_ecu", "brake_ecu"))

	viewer.parse_file_btn()

	names = {viewer.a2lTree.topLevelItem(i).text(0) for i in range(viewer.a2lTree.topLevelItemCount())}
	assert names == {"engine_ecu", "brake_ecu"}


def test_parse_file_btn_only_adds_category_rows_for_non_empty_categories(qapp, monkeypatch, tmp_path):
	a2l_file = tmp_path / "sample.a2l"
	a2l_file.write_bytes(b"")
	tree = _build_tree("test_module")
	module = tree.PROJECT.MODULE[0]
	module.MEASUREMENT.add().Name.Value = "rpm"
	# No CHARACTERISTIC, COMPU_METHOD, etc. entries added.
	viewer = A2LViewer(None)
	viewer.a2l_file = str(a2l_file)
	_patch_parser(monkeypatch, tree = tree)

	viewer.parse_file_btn()

	module_item = viewer.a2lTree.topLevelItem(0)
	category_labels = [module_item.child(i).text(0) for i in range(module_item.childCount())]
	assert category_labels == ["Measurements (1)"]


def test_parse_file_btn_nests_entries_under_their_category(qapp, monkeypatch, tmp_path):
	a2l_file = tmp_path / "sample.a2l"
	a2l_file.write_bytes(b"")
	tree = _build_tree("test_module")
	module = tree.PROJECT.MODULE[0]
	module.MEASUREMENT.add().Name.Value = "rpm"
	module.MEASUREMENT.add().Name.Value = "coolant_temp"
	viewer = A2LViewer(None)
	viewer.a2l_file = str(a2l_file)
	_patch_parser(monkeypatch, tree = tree)

	viewer.parse_file_btn()

	module_item = viewer.a2lTree.topLevelItem(0)
	measurements_item = module_item.child(0)
	assert measurements_item.text(0) == "Measurements (2)"
	entry_names = {measurements_item.child(i).text(0) for i in range(measurements_item.childCount())}
	assert entry_names == {"rpm", "coolant_temp"}


def test_parse_file_btn_clears_the_previous_tree_before_repopulating(qapp, monkeypatch, tmp_path):
	a2l_file = tmp_path / "sample.a2l"
	a2l_file.write_bytes(b"")
	viewer = A2LViewer(None)
	viewer.a2l_file = str(a2l_file)
	_patch_parser(monkeypatch, tree = _build_tree("first_module"))
	viewer.parse_file_btn()
	assert viewer.a2lTree.topLevelItemCount() == 1

	_patch_parser(monkeypatch, tree = _build_tree("second_module", "third_module"))
	viewer.parse_file_btn()

	assert viewer.a2lTree.topLevelItemCount() == 2
	names = {viewer.a2lTree.topLevelItem(i).text(0) for i in range(viewer.a2lTree.topLevelItemCount())}
	assert names == {"second_module", "third_module"}


# --- file selection / persistence --------------------------------------------


def test_init_restores_a_previously_stored_a2l_file(qapp, isolated_paths):
	StoredSettings.A2L_FILE.set("C:/boards/engine.a2l")

	viewer = A2LViewer(None)

	assert viewer.a2lFileLineEdit.text() == "C:/boards/engine.a2l"


def test_load_a2l_persists_the_chosen_path_and_updates_the_line_edit(qapp, isolated_paths, monkeypatch):
	monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: ("C:/boards/engine.a2l", "")))
	viewer = A2LViewer(None)

	viewer.load_a2l()

	assert viewer.a2l_file == "C:/boards/engine.a2l"
	assert viewer.a2lFileLineEdit.text() == "C:/boards/engine.a2l"
	assert StoredSettings.A2L_FILE.get() == "C:/boards/engine.a2l"


def test_load_a2l_does_nothing_when_the_dialog_is_cancelled(qapp, isolated_paths, monkeypatch):
	monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: ("", "")))
	viewer = A2LViewer(None)

	viewer.load_a2l()

	assert viewer.a2l_file is None
	assert StoredSettings.A2L_FILE.get() is None


def test_a2l_line_edit_changed_persists_a_path_that_exists_on_disk(qapp, isolated_paths, tmp_path):
	a2l_file = tmp_path / "engine.a2l"
	a2l_file.write_bytes(b"")
	viewer = A2LViewer(None)
	viewer.a2lFileLineEdit.setText(str(a2l_file))

	viewer.a2lLineEditChanged()

	assert viewer.a2l_file == str(a2l_file)
	assert StoredSettings.A2L_FILE.get() == str(a2l_file)


def test_a2l_line_edit_changed_ignores_a_path_that_does_not_exist(qapp, isolated_paths):
	viewer = A2LViewer(None)
	viewer.a2l_file = None
	viewer.a2lFileLineEdit.setText("C:/does/not/exist.a2l")

	viewer.a2lLineEditChanged()

	assert viewer.a2l_file is None
	assert StoredSettings.A2L_FILE.get() is None
