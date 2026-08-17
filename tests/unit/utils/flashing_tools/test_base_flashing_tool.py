from PySide6.QtGui import QColor, QFont, QTextCharFormat
from PySide6.QtWidgets import QProgressBar, QTextEdit

from fixtures.toml_samples import write_tool_toml
from utils.flashing_tools.base_flashing_tool import BaseFlashingTool


def _make_tool(qapp, tmp_path, **toml_overrides) -> BaseFlashingTool:
	tool_path = write_tool_toml(tmp_path, **toml_overrides)
	tool = BaseFlashingTool(str(tool_path))
	tool.set_log_box(QTextEdit())
	tool.set_progress_bar(QProgressBar())
	return tool


def tool(qapp, tmp_path) -> BaseFlashingTool:
	# "none" so write()'s internal update_progress_bar() call is a no-op,
	# keeping these tests focused on ANSI/carriage-return handling alone.
	return _make_tool(qapp, tmp_path, progress_bar_method="none")


# --- _apply_sgr ---------------------------------------------------------


def test_apply_sgr_sets_bold(qapp, tmp_path):
	t = tool(qapp, tmp_path)
	t._apply_sgr("1")

	assert t._ansi_format.fontWeight() == QFont.Weight.Bold


def test_apply_sgr_sets_foreground_color(qapp, tmp_path):
	t = tool(qapp, tmp_path)
	t._apply_sgr("31")

	assert t._ansi_format.foreground().color() == QColor("#cd3131")


def test_apply_sgr_sets_background_color(qapp, tmp_path):
	t = tool(qapp, tmp_path)
	t._apply_sgr("41")

	# Background SGR codes (40-47) reuse the same palette as the matching
	# foreground code (30-37) via "code - 10".
	assert t._ansi_format.background().color() == QColor("#cd3131")


def test_apply_sgr_combines_multiple_codes_in_one_sequence(qapp, tmp_path):
	t = tool(qapp, tmp_path)
	t._apply_sgr("1;32")

	assert t._ansi_format.fontWeight() == QFont.Weight.Bold
	assert t._ansi_format.foreground().color() == QColor("#0dbc79")


def test_apply_sgr_reset_clears_all_styling(qapp, tmp_path):
	t = tool(qapp, tmp_path)
	t._apply_sgr("1;31")
	t._apply_sgr("0")

	assert t._ansi_format == QTextCharFormat()


def test_apply_sgr_empty_params_defaults_to_reset(qapp, tmp_path):
	t = tool(qapp, tmp_path)
	t._apply_sgr("1;31")
	t._apply_sgr("")

	assert t._ansi_format == QTextCharFormat()


# --- write ---------------------------------------------------------------


def test_write_appends_plain_text(qapp, tmp_path):
	t = tool(qapp, tmp_path)
	t.write("hello")

	assert t.log_box.toPlainText() == "hello"


def test_write_returns_character_count(qapp, tmp_path):
	t = tool(qapp, tmp_path)

	assert t.write("hello") == 5


def test_write_with_empty_string_is_a_noop(qapp, tmp_path):
	t = tool(qapp, tmp_path)

	assert t.write("") == 0
	assert t.log_box.toPlainText() == ""


def test_write_handles_carriage_return_line_overwrite(qapp, tmp_path):
	# esptool-style progress output overwrites the current line with \r
	# rather than appending a new one.
	t = tool(qapp, tmp_path)
	t.write("progress: 10%")
	t.write("\rprogress: 20%")

	assert t.log_box.toPlainText() == "progress: 20%"


def test_write_strips_ansi_sgr_codes_from_visible_text(qapp, tmp_path):
	t = tool(qapp, tmp_path)
	t.write("\x1b[31mred text\x1b[0m")

	assert t.log_box.toPlainText() == "red text"


# --- update_progress_bar --------------------------------------------------


def test_update_progress_bar_step_array_counts_marker_occurrences(qapp, tmp_path):
	# Matches the real avrdude.toml config: method="step_array", one "#"
	# marker, num_steps=100 (so each match advances the bar by 1).
	t = _make_tool(qapp, tmp_path, progress_bar_method="step_array", progress_bar_num_steps=100)
	# A fresh QProgressBar's value() defaults to -1 ("undetermined"); real
	# usage always calls flash()'s p_bar.setValue(0) before any progress
	# updates happen, so match that instead of the raw default.
	t.p_bar.setMaximum(100)
	t.p_bar.setValue(0)

	t.update_progress_bar("####")

	assert t.p_bar.value() == 4


def test_update_progress_bar_regex_normal_reads_current_and_total_counts(qapp, tmp_path):
	# Matches the real esp32.toml config's regexes.
	t = _make_tool(
		qapp,
		tmp_path,
		progress_bar_method="regex",
		regex_method="normal",
		step_read_regex=r"\d+(?=/)",
		step_final_regex=r"(?<=/)\d+",
	)

	t.update_progress_bar("Writing... 12/50")

	assert t.p_bar.value() == 12
	assert t.p_bar.maximum() == 50


def test_update_progress_bar_regex_hex_tracks_address_range_across_calls(qapp, tmp_path):
	t = _make_tool(
		qapp,
		tmp_path,
		progress_bar_method="regex",
		regex_method="hex",
		initial_address=r"(?<=Initial address: )0x[0-9A-Fa-f]+",
		final_address=r"(?<=Final address: )0x[0-9A-Fa-f]+",
		next_address=r"(?<=Writing at: )0x[0-9A-Fa-f]+",
	)

	t.update_progress_bar("Initial address: 0x1000")
	t.update_progress_bar("Final address: 0x2000")
	t.update_progress_bar("Writing at: 0x1800")

	assert t.p_bar.maximum() == 0x2000 - 0x1000
	assert t.p_bar.value() == 0x1800 - 0x1000
