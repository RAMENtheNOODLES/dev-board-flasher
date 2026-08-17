import pytest

from utils.board_utils.board_type import BoardType, get_board_type


@pytest.mark.parametrize(
	"name,expected",
	[
		("ARDUINO", BoardType.ARDUINO),
		("arduino", BoardType.ARDUINO),
		("Arduino", BoardType.ARDUINO),
		("ESPIDF", BoardType.ESPIDF),
		("espidf", BoardType.ESPIDF),
		("CUSTOM", BoardType.CUSTOM),
		("UNKNOWN", BoardType.UNKNOWN),
	],
)
def test_get_board_type_matches_case_insensitively(name, expected):
	assert get_board_type(name) == expected


@pytest.mark.parametrize("name", ["not_a_real_type", "", "arduino "])
def test_get_board_type_falls_back_to_unknown(name):
	assert get_board_type(name) == BoardType.UNKNOWN
