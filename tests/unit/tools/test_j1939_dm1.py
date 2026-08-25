import pytest

from tools.j1939_dm1 import (
	DM1_PGN,
	Dm1TransportDecoder,
	decode_dm1_payload,
	load_fmi_names,
	load_spn_names,
)


def _dtc_bytes(spn: int, fmi: int, occurrence_count: int, spn_conversion_method: int) -> bytes:
	return bytes([
		spn & 0xFF,
		(spn >> 8) & 0xFF,
		((spn >> 16) & 0x7) << 5 | fmi,
		(spn_conversion_method << 7) | occurrence_count,
	])


def test_decode_dm1_payload_returns_none_when_shorter_than_the_lamp_status_bytes():
	assert decode_dm1_payload(0x00, b"\x01") is None


def test_decode_dm1_payload_decodes_lamp_status_bits_for_all_four_lamps():
	# byte 1 (status): MIL=On(01), RSL=Off(00), AWL=On(01), PL=Reserved(10)
	status_byte = 0b10_01_00_01
	# byte 2 (flash): MIL=FastFlash(01), rest=SlowFlash(00)
	flash_byte = 0b00_00_00_01

	msg = decode_dm1_payload(0x00, bytes([status_byte, flash_byte]))

	assert msg.lamp_status.malfunction_indicator.status == "On"
	assert msg.lamp_status.malfunction_indicator.flash == "Fast Flash"
	assert msg.lamp_status.red_stop.status == "Off"
	assert msg.lamp_status.amber_warning.status == "On"
	assert msg.lamp_status.protect.status == "Reserved"
	assert msg.dtcs == ()


def test_decode_dm1_payload_decodes_a_single_dtc_record():
	payload = bytes([0x00, 0x00]) + _dtc_bytes(spn=1234, fmi=3, occurrence_count=5, spn_conversion_method=1)

	msg = decode_dm1_payload(0x17, payload)

	assert msg.source_address == 0x17
	assert len(msg.dtcs) == 1
	dtc = msg.dtcs[0]
	assert (dtc.spn, dtc.fmi, dtc.occurrence_count, dtc.spn_conversion_method) == (1234, 3, 5, 1)


def test_decode_dm1_payload_decodes_multiple_dtc_records():
	payload = (
		bytes([0x00, 0x00])
		+ _dtc_bytes(spn=1234, fmi=3, occurrence_count=5, spn_conversion_method=1)
		+ _dtc_bytes(spn=5678, fmi=7, occurrence_count=2, spn_conversion_method=0)
	)

	msg = decode_dm1_payload(0x00, payload)

	assert [dtc.spn for dtc in msg.dtcs] == [1234, 5678]


def test_decode_dm1_payload_stops_at_all_0xff_padding_record():
	"""A single-frame DM1 with unused DTC slots pads them with 0xFF - those aren't real DTCs."""
	payload = bytes([0x00, 0x00]) + _dtc_bytes(spn=1234, fmi=3, occurrence_count=5, spn_conversion_method=1)
	payload += b"\xff\xff\xff\xff"

	msg = decode_dm1_payload(0x00, payload)

	assert len(msg.dtcs) == 1


def _bam_control_frame(total_size: int, packet_count: int, transported_pgn: int) -> bytes:
	return bytes([
		0x20,
		total_size & 0xFF,
		(total_size >> 8) & 0xFF,
		packet_count,
		0xFF,
		transported_pgn & 0xFF,
		(transported_pgn >> 8) & 0xFF,
		0x00,
	])


# CAN ids (extended, priority=6, page=0): TP.CM (PGN 0xEC00) and TP.DT (PGN
# 0xEB00), both broadcast (PS=0xFF) from source address 0x17.
_TP_CM_ID = 0x18ECFF17
_TP_DT_ID = 0x18EBFF17
_DM1_ID = (0x18000000) | (DM1_PGN << 8) | 0x17


def test_feed_decodes_a_direct_single_frame_dm1_message():
	decoder = Dm1TransportDecoder()
	payload = bytes([0x00, 0x00]) + _dtc_bytes(spn=1234, fmi=3, occurrence_count=5, spn_conversion_method=1)

	result = decoder.feed(_DM1_ID, payload)

	assert result is not None
	assert result.source_address == 0x17
	assert result.dtcs[0].spn == 1234


def test_feed_reassembles_a_bam_sequence_across_multiple_tp_dt_frames():
	dtcs_payload = bytes([0x00, 0x00]) + b"".join(
		_dtc_bytes(spn, fmi=1, occurrence_count=1, spn_conversion_method=0) for spn in (100, 200, 300)
	)
	total_size = len(dtcs_payload)
	packet_count = (total_size + 6) // 7

	decoder = Dm1TransportDecoder()
	assert decoder.feed(_TP_CM_ID, _bam_control_frame(total_size, packet_count, DM1_PGN)) is None

	result = None
	for seq in range(1, packet_count + 1):
		chunk = dtcs_payload[(seq - 1) * 7 : seq * 7]
		chunk = chunk + bytes(7 - len(chunk))
		result = decoder.feed(_TP_DT_ID, bytes([seq]) + chunk)

	assert result is not None
	assert [dtc.spn for dtc in result.dtcs] == [100, 200, 300]


def test_feed_drops_reassembly_state_on_an_out_of_order_sequence_number():
	decoder = Dm1TransportDecoder()
	decoder.feed(_TP_CM_ID, _bam_control_frame(total_size=10, packet_count=2, transported_pgn=DM1_PGN))

	# Sequence 2 arrives before sequence 1 was ever seen.
	result = decoder.feed(_TP_DT_ID, bytes([2]) + bytes(7))

	assert result is None
	# The dropped state shouldn't accept a "correct" sequence 1 afterwards either.
	assert decoder.feed(_TP_DT_ID, bytes([1]) + bytes(7)) is None


def test_feed_ignores_tp_dt_frames_with_no_matching_bam_announcement():
	decoder = Dm1TransportDecoder()

	assert decoder.feed(_TP_DT_ID, bytes([1]) + bytes(7)) is None


def test_feed_clears_pending_dm1_state_when_a_bam_announces_an_unrelated_pgn():
	decoder = Dm1TransportDecoder()
	decoder.feed(_TP_CM_ID, _bam_control_frame(total_size=10, packet_count=2, transported_pgn=DM1_PGN))

	other_pgn = 0xFEE0
	decoder.feed(_TP_CM_ID, _bam_control_frame(total_size=5, packet_count=1, transported_pgn=other_pgn))

	# The DM1 reassembly was abandoned, so a leftover TP.DT for it shouldn't resume it.
	assert decoder.feed(_TP_DT_ID, bytes([1]) + bytes(7)) is None


def test_feed_ignores_frames_for_unrelated_pgns():
	decoder = Dm1TransportDecoder()

	# Some arbitrary, unrelated PGN - not DM1, TP.CM, or TP.DT.
	unrelated_id = 0x18FF0017
	assert decoder.feed(unrelated_id, bytes(8)) is None


def test_load_spn_names_parses_a_two_column_csv(tmp_path):
	csv_path = tmp_path / "spns.csv"
	csv_path.write_text("spn,name\n100,Engine Oil Pressure\n190,Engine Speed\n", encoding="utf-8")

	names = load_spn_names(csv_path)

	assert names == {100: "Engine Oil Pressure", 190: "Engine Speed"}


def test_load_spn_names_skips_blank_rows(tmp_path):
	csv_path = tmp_path / "spns.csv"
	csv_path.write_text("spn,name\n100,Engine Oil Pressure\n\n190,Engine Speed\n", encoding="utf-8")

	names = load_spn_names(csv_path)

	assert names == {100: "Engine Oil Pressure", 190: "Engine Speed"}


def test_load_spn_names_raises_on_a_non_numeric_spn_column(tmp_path):
	csv_path = tmp_path / "spns.csv"
	csv_path.write_text("spn,name\nnot-a-number,Engine Oil Pressure\n", encoding="utf-8")

	with pytest.raises(ValueError):
		load_spn_names(csv_path)


def test_load_fmi_names_parses_a_two_column_csv(tmp_path):
	csv_path = tmp_path / "fmis.csv"
	csv_path.write_text(
		"fmi,name\n0,Data Valid But Above Normal Range\n4,Voltage Below Normal\n", encoding="utf-8"
	)

	names = load_fmi_names(csv_path)

	assert names == {0: "Data Valid But Above Normal Range", 4: "Voltage Below Normal"}


def test_load_fmi_names_raises_on_a_non_numeric_fmi_column(tmp_path):
	csv_path = tmp_path / "fmis.csv"
	csv_path.write_text("fmi,name\nnot-a-number,Voltage Below Normal\n", encoding="utf-8")

	with pytest.raises(ValueError):
		load_fmi_names(csv_path)
