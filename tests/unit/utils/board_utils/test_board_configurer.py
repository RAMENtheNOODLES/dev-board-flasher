from types import SimpleNamespace

import pytest
from fixtures.toml_samples import write_board_toml

from utils.board_utils.board_config import BoardConfig
from utils.board_utils.board_configurer import BoardConfigurer
from utils.board_utils.board_part_id import BoardPartID
from utils.board_utils.board_type import BoardType
from utils.custom_exceptions import (
	UnknownFlasherType,
	UnknownPartID,
	UnsupportedBoardType,
)


def _fake_flasher_finder(tool):
	return SimpleNamespace(get_flashing_tool=lambda name, board_type: tool)


def _raising_flasher_finder(exc):
	def get_flashing_tool(name, board_type):
		raise exc

	return SimpleNamespace(get_flashing_tool=get_flashing_tool)


def test_read_board_config_builds_a_board_config_for_valid_toml(tmp_path):
	board_path = write_board_toml(
		tmp_path,
		board_name="Arduino UNO R3",
		flasher="avrdude",
		baud_rate=115200,
		board_type="arduino",
		part_id="atmega328p",
	)
	fake_tool = SimpleNamespace(get_supported_file_types=lambda: ["*.hex", "*.bin"])

	config = BoardConfigurer.read_board_config(str(board_path), _fake_flasher_finder(fake_tool))

	assert config == BoardConfig(
		BoardName="Arduino UNO R3",
		Flasher=fake_tool,
		BaudRate=115200,
		PartID=BoardPartID.ATMEGA328P,
		Type=BoardType.ARDUINO,
		SupportedFiles=["*.hex", "*.bin"],
	)


def test_read_board_config_returns_none_for_an_unrecognized_flasher_name(tmp_path):
	# An unknown flasher name is treated as a soft/expected failure (logged
	# as a warning), not a hard error - contrast with the raise below.
	board_path = write_board_toml(tmp_path, flasher="totally_unknown_flasher")
	finder = _raising_flasher_finder(UnknownFlasherType("totally_unknown_flasher"))

	assert BoardConfigurer.read_board_config(str(board_path), finder) is None


def test_read_board_config_propagates_unsupported_board_type(tmp_path):
	board_path = write_board_toml(tmp_path)
	finder = _raising_flasher_finder(
		UnsupportedBoardType(BoardType.ARDUINO, SimpleNamespace(get_name=lambda: "esp32"))
	)

	with pytest.raises(UnsupportedBoardType):
		BoardConfigurer.read_board_config(str(board_path), finder)


def test_read_board_config_raises_for_unknown_part_id(tmp_path):
	board_path = write_board_toml(tmp_path, part_id="not_a_real_part")
	finder = _fake_flasher_finder(SimpleNamespace(get_supported_file_types=list))

	with pytest.raises(UnknownPartID):
		BoardConfigurer.read_board_config(str(board_path), finder)
