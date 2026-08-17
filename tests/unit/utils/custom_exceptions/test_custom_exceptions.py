import pytest

from utils.custom_exceptions import (
	RemoteConfigError,
	UnknownFlasherType,
	UnknownPartID,
	UnsupportedBoardType,
)


@pytest.mark.parametrize(
	"exception_cls", [RemoteConfigError, UnknownFlasherType, UnknownPartID]
)
def test_plain_exceptions_carry_their_message(exception_cls):
	with pytest.raises(exception_cls, match="something went wrong"):
		raise exception_cls("something went wrong")


def test_unsupported_board_type_builds_message_from_board_and_tool():
	# TYPE_CHECKING-only imports mean board/flashing_tool are duck-typed at
	# runtime, so plain stubs exposing just .name/.get_name() are enough.
	board = type("FakeBoardType", (), {"name": "ESPIDF"})()
	flashing_tool = type("FakeFlashingTool", (), {"get_name": lambda self: "avrdude"})()

	error = UnsupportedBoardType(board, flashing_tool)

	assert "ESPIDF" in str(error)
	assert "avrdude" in str(error)
