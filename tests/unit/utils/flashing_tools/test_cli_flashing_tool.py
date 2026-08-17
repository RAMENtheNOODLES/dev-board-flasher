from PySide6.QtWidgets import QProgressBar

from fixtures.toml_samples import write_tool_toml
from utils.board_utils.board_config import BoardConfig
from utils.board_utils.board_part_id import BoardPartID
from utils.board_utils.board_type import BoardType
from utils.flashing_tools.cli_flashing_tool import CLIFlashingTool


def _make_tool(qapp, tmp_path, mocker, **toml_overrides) -> CLIFlashingTool:
	tool_path = write_tool_toml(tmp_path, tool_type="cli", **toml_overrides)
	tool = CLIFlashingTool(str(tool_path))
	tool.set_progress_bar(QProgressBar())
	# flash()'s only real side effect is process.start(); mock it out so
	# tests never actually spawn a CLI process.
	tool.process = mocker.MagicMock()
	return tool


def _make_board(**overrides) -> BoardConfig:
	defaults = dict(
		BoardName="Arduino UNO R3",
		Flasher=None,
		BaudRate=115200,
		PartID=BoardPartID.ATMEGA328P,
		Type=BoardType.ARDUINO,
		SupportedFiles=["*.hex"],
	)
	defaults.update(overrides)
	return BoardConfig(**defaults)


def test_flash_substitutes_template_variables_into_args(qapp, tmp_path, mocker):
	# The real avrdude.toml "default" preset, for realism.
	tool = _make_tool(
		qapp,
		tmp_path,
		mocker,
		tool_name="avrdude",
		custom_settings={
			"default": [
				"-c", "arduino", "-p", "$partid", "-P", "$port",
				"-b", "$baudrate", "-D", "-U", "flash:w:$file:i",
			],
		},
	)
	board = _make_board()

	result = tool.flash(board, port="COM3", file="firmware.hex")

	assert result is True
	tool.process.start.assert_called_once_with(
		"avrdude",
		["-c", "arduino", "-p", "ATMEGA328P", "-P", "COM3", "-b", "115200", "-D", "-U", "flash:w:firmware.hex:i"],
	)


def test_flash_falls_back_to_tool_name_when_tool_loc_is_unset(qapp, tmp_path, mocker):
	tool = _make_tool(qapp, tmp_path, mocker, tool_name="avrdude", tool_loc="", custom_settings={"default": []})
	board = _make_board()

	tool.flash(board, port="COM3", file="firmware.hex")

	tool.process.start.assert_called_once_with("avrdude", [])


def test_flash_uses_tool_loc_when_set(qapp, tmp_path, mocker):
	tool = _make_tool(qapp, tmp_path, mocker, tool_loc="C:/tools/avrdude.exe", custom_settings={"default": []})
	board = _make_board()

	tool.flash(board, port="COM3", file="firmware.hex")

	tool.process.start.assert_called_once_with("C:/tools/avrdude.exe", [])


def test_flash_with_unrecognized_settings_name_runs_with_no_args(qapp, tmp_path, mocker):
	tool = _make_tool(qapp, tmp_path, mocker, custom_settings={"default": ["-p", "$partid"]})
	board = _make_board()

	tool.flash(board, port="COM3", file="firmware.hex", settings="nonexistent")

	tool.process.start.assert_called_once_with(tool.name, [])


def test_flash_selects_the_named_settings_preset(qapp, tmp_path, mocker):
	tool = _make_tool(
		qapp,
		tmp_path,
		mocker,
		custom_settings={
			"default": ["-p", "$partid"],
			"dry_run": ["-n", "-p", "$partid"],
		},
	)
	board = _make_board()

	tool.flash(board, port="COM3", file="firmware.hex", settings="dry_run")

	tool.process.start.assert_called_once_with(tool.name, ["-n", "-p", "ATMEGA328P"])
