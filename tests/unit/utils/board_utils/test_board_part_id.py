import pytest

from utils.board_utils.board_part_id import BoardPartID, get_board_part_id
from utils.custom_exceptions import UnknownPartID


@pytest.mark.parametrize(
	"name,expected",
	[
		("ATMEGA328P", BoardPartID.ATMEGA328P),
		("atmega328p", BoardPartID.ATMEGA328P),
		("Atmega328p", BoardPartID.ATMEGA328P),
		("UNDEF", BoardPartID.UNDEF),
		("undef", BoardPartID.UNDEF),
	],
)
def test_get_board_part_id_matches_case_insensitively(name, expected):
	assert get_board_part_id(name) == expected


@pytest.mark.parametrize("name", ["not_a_real_part", "", "atmega328p "])
def test_get_board_part_id_raises_on_unknown(name):
	# Contrast with board_type.get_board_type: an unmatched part id raises
	# rather than silently falling back to a placeholder member, since an
	# unrecognized part id means the board config itself is wrong.
	with pytest.raises(UnknownPartID):
		get_board_part_id(name)
