from types import SimpleNamespace

import pytest
from fixtures.toml_samples import write_tool_toml

from utils.board_utils.board_type import BoardType
from utils.board_utils.flasher_finder import FlasherFinder
from utils.custom_exceptions import UnknownFlasherType, UnsupportedBoardType
from utils.flashing_tools.cli_flashing_tool import CLIFlashingTool
from utils.flashing_tools.esp32 import ESP32


def test_parse_tools_builds_a_cli_flashing_tool_for_cli_type(qapp, tmp_path):
	tool_path = write_tool_toml(tmp_path, tool_name="avrdude", tool_type="cli")

	tools = FlasherFinder.parse_tools([str(tool_path)])

	assert isinstance(tools["avrdude"], CLIFlashingTool)


def test_parse_tools_builds_esp32_for_python_type_named_esp32(qapp, tmp_path):
	tool_path = write_tool_toml(
		tmp_path, tool_name="esp32", tool_type="python", supported_boards=["ESPIDF"]
	)

	tools = FlasherFinder.parse_tools([str(tool_path)])

	assert isinstance(tools["esp32"], ESP32)


def test_parse_tools_raises_for_unrecognized_python_tool_name(qapp, tmp_path):
	tool_path = write_tool_toml(tmp_path, tool_name="some_other_tool", tool_type="python")

	with pytest.raises(UnknownFlasherType):
		FlasherFinder.parse_tools([str(tool_path)])


def test_parse_tools_raises_for_unknown_tool_type(tmp_path):
	tool_path = write_tool_toml(tmp_path, tool_name="mystery", tool_type="rust")

	with pytest.raises(UnknownFlasherType):
		FlasherFinder.parse_tools([str(tool_path)])


def _bare_finder(tools: dict) -> FlasherFinder:
	"""Builds a FlasherFinder without running __init__ (which scans the real
	bundled config/flashing_tools directory on disk), for tests that only
	exercise get_flashing_tool() against a controlled `tools` dict."""
	finder = FlasherFinder.__new__(FlasherFinder)
	finder.tools = tools
	return finder


def test_get_flashing_tool_returns_the_matching_tool():
	fake_tool = SimpleNamespace(get_supported_boards=lambda: [BoardType.ARDUINO])
	finder = _bare_finder({"avrdude": fake_tool})

	assert finder.get_flashing_tool("avrdude", BoardType.ARDUINO) is fake_tool


def test_get_flashing_tool_raises_unknown_flasher_type_for_missing_name():
	finder = _bare_finder({})

	with pytest.raises(UnknownFlasherType):
		finder.get_flashing_tool("nonexistent", BoardType.ARDUINO)


def test_get_flashing_tool_raises_unsupported_board_type_for_mismatched_board():
	fake_tool = SimpleNamespace(
		get_supported_boards=lambda: [BoardType.ESPIDF],
		get_name=lambda: "esp32",
	)
	finder = _bare_finder({"esp32": fake_tool})

	with pytest.raises(UnsupportedBoardType):
		finder.get_flashing_tool("esp32", BoardType.ARDUINO)
