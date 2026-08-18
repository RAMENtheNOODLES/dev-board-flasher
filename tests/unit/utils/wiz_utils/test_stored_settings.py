import pytest

from utils.wiz_utils.stored_settings import StoredSettings, universal_to_bytes


def test_universal_to_bytes_passes_through_bytes():
	assert universal_to_bytes(b"already bytes") == b"already bytes"


def test_universal_to_bytes_encodes_strings_as_utf8():
	assert universal_to_bytes("hello") == "hello".encode("utf-8")


@pytest.mark.parametrize(
	"value",
	[
		0, 1, -1, 65536,
		# Values whose magnitude's bit_length lands exactly on a byte
		# boundary - the previously-buggy case (see stored_settings.py).
		127, 128, 255, -128, -129, 32767, 32768,
	],
)
def test_universal_to_bytes_round_trips_integers(value):
	encoded = universal_to_bytes(value)
	assert isinstance(encoded, bytes)
	assert int.from_bytes(encoded, byteorder="big", signed=True) == value


def test_universal_to_bytes_does_not_treat_bools_as_ints():
	# isinstance(True, int) is True in Python, so this has to be checked
	# explicitly ahead of the int branch or booleans would silently get the
	# wrong (1-byte signed-int) encoding instead of going through the
	# JSON-serializable branch like other non-int JSON types.
	assert universal_to_bytes(True) == b"true"
	assert universal_to_bytes(False) == b"false"


def test_universal_to_bytes_json_encodes_other_serializable_types():
	assert universal_to_bytes([1, 2, 3]) == b"[1, 2, 3]"
	assert universal_to_bytes({"a": 1}) == b'{"a": 1}'
	assert universal_to_bytes(1.5) == b"1.5"


def test_universal_to_bytes_falls_back_to_str_for_non_serializable_objects():
	class NotJsonSerializable:
		def __str__(self):
			return "custom repr"

	assert universal_to_bytes(NotJsonSerializable()) == b"custom repr"


def test_get_set_round_trip(isolated_paths):
	StoredSettings.CHOSEN_BOARD.set("Arduino UNO R3")

	assert StoredSettings.CHOSEN_BOARD.get() == "Arduino UNO R3"


def test_get_returns_default_when_nothing_stored(isolated_paths):
	assert StoredSettings.CHOSEN_BOARD.get("fallback") == "fallback"


def test_secure_set_get_round_trip(isolated_paths):
	StoredSettings.REMOTE_CONFIGS.secure_set(["a.toml", "b.toml"])

	assert StoredSettings.REMOTE_CONFIGS.secure_get() == ["a.toml", "b.toml"]


def test_secure_get_returns_default_when_nothing_stored(isolated_paths):
	assert StoredSettings.REMOTE_CONFIGS.secure_get(["fallback"]) == ["fallback"]


def test_secure_set_with_ttl_zero_expires_immediately(isolated_paths):
	StoredSettings.REMOTE_CONFIGS.secure_set(["a.toml"], ttl_seconds=0)

	assert StoredSettings.REMOTE_CONFIGS.secure_get(["fallback"]) == ["fallback"]


def test_secure_set_with_no_ttl_never_expires(isolated_paths):
	# ttl_seconds defaults to None, which diskcache treats as "no expiry".
	StoredSettings.REMOTE_CONFIGS.secure_set(["a.toml"])

	assert StoredSettings.REMOTE_CONFIGS.secure_get() == ["a.toml"]
