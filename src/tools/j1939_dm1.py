"""Parsing for SAE J1939 DM1 (Active Diagnostic Trouble Codes) messages.

DM1 (PGN 0xFECA) is broadcast periodically by every J1939 ECU that currently
has at least one active fault. Its payload is 2 lamp-status bytes followed
by one 4-byte record per active DTC (SPN + FMI + occurrence count + SPN
conversion method) - see SAE J1939-73. That only fits an 8-byte CAN frame
when 0-1 DTCs are active; ECUs reporting more use the SAE J1939-21 BAM
transport protocol (TP.CM + TP.DT), which :class:`Dm1TransportDecoder`
reassembles.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from canlib import j1939

#: PGN of the DM1 message itself.
DM1_PGN = 0xFECA
#: PGN of a BAM's announcement (TP.CM) frame. The broadcast destination
#: (0xFF) is carried separately, in the CAN id's PDU-specific field.
_TP_CM_PGN = 0xEC00
#: PGN of a BAM's data-transfer (TP.DT) frames.
_TP_DT_PGN = 0xEB00
#: TP.CM control byte identifying a Broadcast Announce Message, as opposed
#: to a point-to-point RTS/CTS session - DM1 is always broadcast, so that's
#: the only kind this needs to reassemble.
_BAM_CONTROL_BYTE = 0x20

# SAE J1939-73 2-bit lamp status/flash codes. Byte 1 (status) and byte 2
# (flash) of a DM1 message each pack 4 lamps' worth of these into the same
# bit layout: bits 1-2 = MIL, 3-4 = Red Stop Lamp, 5-6 = Amber Warning Lamp,
# 7-8 = Protect Lamp.
_LAMP_STATUS_LABELS = {0b00: "Off", 0b01: "On", 0b10: "Reserved", 0b11: "Not Available"}
_LAMP_FLASH_LABELS = {0b00: "Slow Flash", 0b01: "Fast Flash", 0b10: "Reserved", 0b11: "Not Flashing"}


@dataclass(frozen=True)
class Lamp:
    """A single dashboard lamp's decoded status/flash state."""

    status: str
    flash: str


@dataclass(frozen=True)
class LampStatus:
    """The 4 lamps reported by every DM1 message, decoded from its first 2 bytes."""

    malfunction_indicator: Lamp
    red_stop: Lamp
    amber_warning: Lamp
    protect: Lamp


@dataclass(frozen=True)
class Dtc:
    """A single active Diagnostic Trouble Code from a DM1 message."""

    spn: int  #: Suspect Parameter Number identifying the faulting parameter.
    fmi: int  #: Failure Mode Identifier, e.g. "above normal range".
    occurrence_count: int  #: Number of times this fault has been detected.
    spn_conversion_method: int  #: SPN Conversion Method bit (0 or 1); see SAE J1939-73.


@dataclass(frozen=True)
class Dm1Message:
    """A fully decoded DM1 message from one source address."""

    source_address: int
    lamp_status: LampStatus
    dtcs: tuple[Dtc, ...]


def _decode_lamp_status(status_byte: int, flash_byte: int) -> LampStatus:
    def lamp(bit_offset: int) -> Lamp:
        return Lamp(
            status=_LAMP_STATUS_LABELS[(status_byte >> bit_offset) & 0b11],
            flash=_LAMP_FLASH_LABELS[(flash_byte >> bit_offset) & 0b11],
        )

    return LampStatus(
        malfunction_indicator=lamp(0),
        red_stop=lamp(2),
        amber_warning=lamp(4),
        protect=lamp(6),
    )


def _decode_dtc(record: bytes) -> Dtc | None:
    """Decodes one 4-byte DTC record, or `None` if it's unused-slot padding (all 0xFF)."""
    if record == b"\xff\xff\xff\xff":
        return None

    spn = record[0] | (record[1] << 8) | ((record[2] >> 5) << 16)
    fmi = record[2] & 0x1F
    spn_conversion_method = (record[3] >> 7) & 0b1
    occurrence_count = record[3] & 0x7F
    return Dtc(spn=spn, fmi=fmi, occurrence_count=occurrence_count, spn_conversion_method=spn_conversion_method)


def decode_dm1_payload(source_address: int, payload: bytes) -> Dm1Message | None:
    """Decodes a complete DM1 payload (already reassembled, if it arrived via BAM).

    Returns `None` if `payload` is too short to even contain lamp status.
    Stops at the first all-0xFF DTC record, since that means the rest of a
    single (non-BAM) frame is just unused-slot padding rather than real DTCs.
    """
    if len(payload) < 2:
        return None

    lamp_status = _decode_lamp_status(payload[0], payload[1])

    dtcs = []
    for offset in range(2, len(payload) - 3, 4):
        dtc = _decode_dtc(payload[offset:offset + 4])
        if dtc is None:
            break
        dtcs.append(dtc)

    return Dm1Message(source_address=source_address, lamp_status=lamp_status, dtcs=tuple(dtcs))


def _load_int_name_csv(path: str | Path) -> dict[int, str]:
	"""Loads a 2-column ``<int code>,<name>`` CSV file into a lookup dict.

	Blank rows are skipped. Raises `ValueError` if a non-blank row's first
	column isn't a valid integer.
	"""
	names: dict[int, str] = {}
	with Path(path).open(newline="", encoding="utf-8-sig") as csv_file:
		reader = csv.reader(csv_file)
		next(reader, None)  # header row
		for row in reader:
			if not row:
				continue
			code_text, name = row[0], row[1]
			names[int(code_text.strip())] = name.strip()

	return names


def load_spn_names(path: str | Path) -> dict[int, str]:
	"""Loads an SPN-to-name lookup table from a 2-column CSV file.

	The file must have a header row followed by ``spn,name`` rows, e.g.::

		spn,name
		100,Engine Oil Pressure
		190,Engine Speed
	"""
	return _load_int_name_csv(path)


def load_fmi_names(path: str | Path) -> dict[int, str]:
	"""Loads an FMI-to-name lookup table from a 2-column CSV file.

	The file must have a header row followed by ``fmi,name`` rows, e.g.::

		fmi,name
		0,Data Valid But Above Normal Range
		4,Voltage Below Normal
	"""
	return _load_int_name_csv(path)


@dataclass
class _PendingBam:
    total_size: int
    packet_count: int
    next_sequence: int
    buffer: bytearray


class Dm1TransportDecoder:
    """Reassembles DM1 messages from raw frames, tracked per source address.

    Feed it every received extended-id frame via :meth:`feed`. It returns a
    decoded :class:`Dm1Message` as soon as one is complete: immediately for
    a single-frame DM1 (an ECU reporting 0-1 DTCs), or once a full BAM
    transport-protocol sequence - a TP.CM announcing the transfer, followed
    by one TP.DT per 7-byte chunk - has been reassembled for an ECU
    reporting more.
    """

    def __init__(self) -> None:
        self._pending: dict[int, _PendingBam] = {}

    def feed(self, frame_id: int, data: bytes) -> Dm1Message | None:
        """Processes one extended-id frame, returning a decoded DM1 message if it just completed one."""
        pdu = j1939.pdu_from_can_id(frame_id)

        if pdu.pgn == DM1_PGN:
            return decode_dm1_payload(pdu.sa, data)
        if pdu.pgn == _TP_CM_PGN:
            self._handle_tp_cm(pdu.sa, data)
            return None
        if pdu.pgn == _TP_DT_PGN:
            return self._handle_tp_dt(pdu.sa, data)
        return None

    def _handle_tp_cm(self, source_address: int, data: bytes) -> None:
        if len(data) < 8 or data[0] != _BAM_CONTROL_BYTE:
            return

        transported_pgn = data[5] | (data[6] << 8) | (data[7] << 16)
        if transported_pgn != DM1_PGN:
            # A BAM for something other than DM1 - drop any stale DM1
            # reassembly for this address rather than risk a stray TP.DT
            # from this new transfer getting appended to it.
            self._pending.pop(source_address, None)
            return

        total_size = data[1] | (data[2] << 8)
        packet_count = data[3]
        self._pending[source_address] = _PendingBam(
            total_size=total_size, packet_count=packet_count, next_sequence=1, buffer=bytearray()
        )

    def _handle_tp_dt(self, source_address: int, data: bytes) -> Dm1Message | None:
        pending = self._pending.get(source_address)
        if pending is None or len(data) < 1:
            return None

        sequence_number = data[0]
        if sequence_number != pending.next_sequence:
            # A gap means the reassembled payload can no longer be trusted -
            # drop it rather than hand back corrupted DTC data.
            del self._pending[source_address]
            return None

        pending.buffer.extend(data[1:8])
        pending.next_sequence += 1

        if sequence_number < pending.packet_count:
            return None

        del self._pending[source_address]
        return decode_dm1_payload(source_address, bytes(pending.buffer[:pending.total_size]))
