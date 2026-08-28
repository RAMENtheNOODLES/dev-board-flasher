import sys

import pytest
from fixtures.toml_samples import write_tool_toml
from PySide6.QtCore import QProcess
from PySide6.QtGui import QColor, QFont, QTextCharFormat
from PySide6.QtWidgets import QProgressBar, QTextEdit

from utils.flashing_tools.base_flashing_tool import BaseFlashingTool

if sys.platform == "win32":
	from utils.flashing_tools.conpty_process import ConPtyProcess


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


# --- use_pty / process backend selection ----------------------------------


def test_process_defaults_to_qprocess_when_use_pty_is_unset(qapp, tmp_path):
	t = _make_tool(qapp, tmp_path)

	assert t.use_pty is False
	assert isinstance(t.process, QProcess)


@pytest.mark.skipif(sys.platform != "win32", reason="ConPtyProcess wraps the Windows ConPTY API")
def test_process_is_conpty_when_use_pty_is_true(qapp, tmp_path):
	t = _make_tool(qapp, tmp_path, use_pty=True)

	assert t.use_pty is True
	assert isinstance(t.process, ConPtyProcess)


# --- stop_on / read_terminal_stream kill behavior --------------------------


def test_read_terminal_stream_kills_process_when_stop_marker_seen(qapp, tmp_path, mocker):
	t = _make_tool(qapp, tmp_path, stop_on=["press enter to exit"])
	t.process = mocker.MagicMock()
	t.process.readAllStandardOutput.return_value.data.return_value = b"Done. press enter to exit"

	t.read_terminal_stream()

	t.process.kill.assert_called_once()
	assert t.log_box.toPlainText() == "Done. press enter to exit"


def test_read_terminal_stream_does_not_kill_process_without_stop_marker(qapp, tmp_path, mocker):
	t = _make_tool(qapp, tmp_path, stop_on=["press enter to exit"])
	t.process = mocker.MagicMock()
	t.process.readAllStandardOutput.return_value.data.return_value = b"Flashing... 50%"

	t.read_terminal_stream()

	t.process.kill.assert_not_called()


def test_read_terminal_stream_never_kills_when_stop_on_is_unset(qapp, tmp_path, mocker):
	t = _make_tool(qapp, tmp_path)
	t.process = mocker.MagicMock()
	t.process.readAllStandardOutput.return_value.data.return_value = b"press enter to exit"

	t.read_terminal_stream()

	t.process.kill.assert_not_called()


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


def test_write_treats_crlf_as_plain_newline_not_line_overwrite(qapp, tmp_path):
	# Real console output (e.g. from a ConPTY-attached process) uses "\r\n"
	# for every line ending, not just for esptool-style progress redraws.
	# That must not erase the previous line the way a lone "\r" does.
	t = tool(qapp, tmp_path)
	t.write("line1\r\nline2\r\n")

	assert t.log_box.toPlainText() == "line1\nline2\n"


def test_write_treats_crlf_split_across_calls_as_plain_newline(qapp, tmp_path):
	# readyReadStandardOutput fires with whatever bytes the OS pipe has
	# buffered at that moment, so a "\r\n" line ending can land with the
	# "\r" as the last byte of one read and the "\n" as the first byte of
	# the next -- two separate write() calls. That split must still be
	# treated as one plain newline, not mistaken for an esptool-style
	# overwrite that erases the line just written.
	t = tool(qapp, tmp_path)
	t.write("line1\r")
	t.write("\nline2\r\n")

	assert t.log_box.toPlainText() == "line1\nline2\n"


def test_write_still_overwrites_line_when_trailing_cr_is_not_followed_by_newline(qapp, tmp_path):
	# A trailing "\r" with no "\n" arriving right after it in the next call
	# is a genuine overwrite (e.g. a progress percentage updating in place
	# across separate write() calls), and must still erase the prior line.
	t = tool(qapp, tmp_path)
	t.write("progress: 10%\r")
	t.write("progress: 20%")

	assert t.log_box.toPlainText() == "progress: 20%"


def test_write_treats_doubled_cr_before_newline_as_plain_newline(qapp, tmp_path):
	# Some CLI tools (e.g. j1939_btl_app.exe) emit "\r\r\n" rather than
	# "\r\n" -- they write "\r\n" explicitly while stdout is still in the
	# C runtime's text mode, which re-translates the embedded "\n" into
	# another "\r\n". A single chunk.replace("\r\n", "\n") only consumes
	# the trailing "\r\n" of that pair, leaving a stray "\r" that gets
	# misread as an esptool-style overwrite and erases the line just
	# written. Every "\r" immediately before a "\n" must collapse away,
	# no matter how many there are.
	t = tool(qapp, tmp_path)
	t.write("line1\r\r\nline2\r\r\n")

	assert t.log_box.toPlainText() == "line1\nline2\n"


def test_write_strips_ansi_sgr_codes_from_visible_text(qapp, tmp_path):
	t = tool(qapp, tmp_path)
	t.write("\x1b[31mred text\x1b[0m")

	assert t.log_box.toPlainText() == "red text"


def test_write_strips_dec_private_mode_sequences(qapp, tmp_path):
	# ConPTY-attached apps commonly emit these on startup (win32-input-mode,
	# focus-tracking); the "?" marker isn't part of a plain SGR sequence, so
	# it needs its own coverage against the CSI regex.
	t = tool(qapp, tmp_path)
	t.write("\x1b[?9001hhello\x1b[?1004h world")

	assert t.log_box.toPlainText() == "hello world"


def test_write_strips_osc_window_title_sequences(qapp, tmp_path):
	# ConPTY-attached apps commonly set the console window title via an OSC
	# sequence (ESC ] 0 ; title BEL), a different escape family from CSI
	# ("ESC [...") that needs its own match branch.
	t = tool(qapp, tmp_path)
	t.write("\x1b]0;C:/tools/flasher.exe\x07Flasher: Failed to detect device")

	assert t.log_box.toPlainText() == "Flasher: Failed to detect device"


# --- read_terminal_stream --------------------------------------------------


def test_read_terminal_stream_strips_ansi_codes_from_process_output(qapp, tmp_path, mocker):
	# ConPTY-backed tools produce real ANSI SGR codes (unlike a plain pipe,
	# which most CLI tools detect and suppress color for); this output
	# should go through the same stripping/parsing as write() rather than
	# landing in the log box as raw escape codes.
	t = tool(qapp, tmp_path)
	t.process = mocker.MagicMock()
	t.process.readAllStandardOutput.return_value.data.return_value = b"\x1b[31mred text\x1b[0m"

	t.read_terminal_stream()

	assert t.log_box.toPlainText() == "red text"


def test_read_terminal_stream_advances_progress_bar(qapp, tmp_path, mocker):
	t = _make_tool(qapp, tmp_path, progress_bar_method="step_array", progress_bar_num_steps=100)
	t.p_bar.setMaximum(100)
	t.p_bar.setValue(0)
	t.process = mocker.MagicMock()
	t.process.readAllStandardOutput.return_value.data.return_value = b"##"

	t.read_terminal_stream()

	assert t.p_bar.value() == 2


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
