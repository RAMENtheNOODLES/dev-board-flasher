import logging
import os
import re

from google.protobuf.message import Message
from pya2l.parser import A2lError, A2lParser
from pya2l.protobuf.A2L_pb2 import ModuleType
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QFileDialog, QMainWindow, QMessageBox, QTreeWidgetItem

from ui_a2l import Ui_A2LViewer
from utils.ui_utils import get_global_font
from utils.wiz_utils.stored_settings import StoredSettings

# Matches whichever comes first, in document order: a `/begin NAME`, an
# `/end NAME`, or a whole quoted string (so a `/begin`/`/end`-shaped substring
# inside a string literal is consumed as part of the string and never
# mistaken for a real block delimiter).
_A2L_BLOCK_TOKEN = re.compile(rb'/begin\s+(\w+)|/end\s+(\w+)|"(?:[^"\\]|\\.)*"')

# `FORMAT`'s printf-style width.precision spec (e.g. `%6.3`) is defined as a
# quoted STRING in the ASAP2 grammar, but some tools export it bare.
_BARE_FORMAT_SPEC = re.compile(rb'(\bFORMAT\s+)(%\d+\.\d+)\b')

# An ASAP2 INT or HEX literal, e.g. `16`, `-1`, `0x2044c7c8`.
_A2L_NUMBER = rb'(?:0[xX][0-9A-Fa-f]+|-?\d+)'
_A2L_NUMBER_RE = re.compile(_A2L_NUMBER)
# `MATRIX_DIM` with 1 or 2 dimensions given (a valid lower-dimensional array
# per the ASAP2 spec), not immediately followed by a 3rd dimension value.
_SHORT_MATRIX_DIM = re.compile(rb'\bMATRIX_DIM(?:\s+' + _A2L_NUMBER + rb'){1,2}\b(?!\s+' + _A2L_NUMBER + rb')')


def _quote_bare_format_specs(data: bytes) -> bytes:
	"""Wraps an unquoted ``FORMAT`` spec (e.g. ``FORMAT %6.3``) in double quotes.

	pya2l's grammar requires ``FORMAT``'s value to be a quoted STRING per the
	ASAP2 spec, but some calibration tools export it bare, which aborts
	parsing of the whole file with a "mismatched input ... expecting STRING"
	error. Unlike :func:`_strip_if_data_blocks`, this can't just delete the
	surrounding block - ``FORMAT`` lives inside ``MEASUREMENT``/``CHARACTERISTIC``
	blocks alongside fields the tree does need - so it quotes the value in
	place instead.

	Args:
		data (bytes): Raw A2L file contents (already past the ``IF_DATA``
			strip, though the order doesn't actually matter between the two).

	Returns:
		bytes: The same content with every bare ``FORMAT`` spec quoted.
	"""
	return _BARE_FORMAT_SPEC.sub(rb'\1"\2"', data)


def _pad_short_matrix_dims(data: bytes) -> bytes:
	"""Pads a ``MATRIX_DIM`` with fewer than 3 dimensions out to 3, trailing zeros.

	The ASAP2 spec allows ``MATRIX_DIM`` to give just the dimensions an array
	actually has (``MATRIX_DIM xDim`` for a 1-D array), but pya2l's grammar
	hardcodes it at exactly 3 (``xDim yDim zDim``) - a 1- or 2-dimension form
	leaves the parser still expecting another ``INT``/``HEX`` when it hits
	whatever real field comes next (usually ``BYTE_ORDER``), aborting parsing
	of the whole file. As with :func:`_quote_bare_format_specs`, ``MATRIX_DIM``
	lives inside a ``CHARACTERISTIC``/``MEASUREMENT`` block alongside fields
	the tree does need, so this pads it in place rather than deleting anything.

	Args:
		data (bytes): Raw A2L file contents.

	Returns:
		bytes: The same content with every short ``MATRIX_DIM`` padded to 3 dimensions.
	"""

	def pad(match: re.Match) -> bytes:
		given = len(_A2L_NUMBER_RE.findall(match.group(0)))
		return match.group(0) + b" 0" * (3 - given)

	return _SHORT_MATRIX_DIM.sub(pad, data)


def _strip_if_data_blocks(data: bytes) -> bytes:
	"""Removes every ``/begin IF_DATA ... /end IF_DATA`` block from raw A2L source.

	``IF_DATA`` holds vendor/tool-specific content (CCP/XCP transport
	parameters, calibration-tool hints, ...) with no fixed schema, and pya2l's
	grammar doesn't reliably parse it: any ASAP2 keyword used as a bare value
	inside one - e.g. a ``DEFINED_PAGES`` memory page literally named ``RAM``
	- fails to parse as an ordinary identifier there, even though the exact
	same word parses fine as, say, a ``MEMORY_SEGMENT``'s memory type, where
	the grammar has a dedicated rule expecting it. That one reserved-word
	collision aborts parsing of the *entire* file. Since :meth:`A2LViewer._populate_module`
	never reads ``IF_DATA`` content in the first place, excising it before
	parsing sidesteps the bug entirely at no loss to what's actually shown.

	Blocks are found by tracking ``/begin``/``/end`` nesting depth rather
	than a naive first-``/end IF_DATA`` search, since real ``IF_DATA`` blocks
	nest further ``/begin``/``/end`` sub-blocks (as in the CCP example above).

	Args:
		data (bytes): Raw A2L file contents.

	Returns:
		bytes: The same content with every ``IF_DATA`` block removed.
	"""
	out = bytearray()
	pos = 0
	depth = 0

	for match in _A2L_BLOCK_TOKEN.finditer(data):
		begin_name, end_name = match.group(1), match.group(2)
		if depth == 0:
			if begin_name == b"IF_DATA":
				out += data[pos:match.start()]
				depth = 1
		else:
			if begin_name is not None:
				depth += 1
			elif end_name is not None:
				depth -= 1
				if depth == 0:
					pos = match.end()

	out += data[pos:]
	return bytes(out)


def _wrapped(message: Message, field_name: str) -> str:
	"""Reads an optional ASAP2 "wrapper" field (e.g. ``IdentType``, ``StringType``) as a string.

	Most scalar fields in the pya2l protobuf schema (names, descriptions,
	...) aren't plain strings - they're wrapped in a small message type
	with a single ``Value`` field, so the parser can distinguish "not
	present in the A2L file" from "present with a default value".
	``HasField`` reflects that presence for the wrapper itself; this returns
	``""`` when it's absent instead of raising, since most rows in the tree
	only fill in a handful of a module's many optional fields.

	Args:
		message (Message): The parent message (e.g. a ``MeasurementType``).
		field_name (str): Name of the wrapper field on ``message``.

	Returns:
		str: The wrapped value as a string, or ``""`` if the field is absent.
	"""
	if not message.HasField(field_name):
		return ""

	return str(getattr(message, field_name).Value)


def _address(message: Message, field_name: str) -> str:
	"""Reads an optional ``LongType``-wrapped address field, formatted as hex.

	Args:
		message (Message): The parent message (e.g. a ``CharacteristicType``).
		field_name (str): Name of the ``LongType`` address field on ``message``.

	Returns:
		str: The address as ``"0x...."``, or ``""`` if the field is absent.
	"""
	if not message.HasField(field_name):
		return ""

	return f"0x{getattr(message, field_name).Value:X}"


def _ecu_address(message: Message, field_name: str) -> str:
	"""Reads an optional ``EcuAddressType`` field, formatted as hex.

	Unlike ``CHARACTERISTIC``/``AXIS_PTS``, whose ``Address`` field is
	directly a ``LongType``, ``MEASUREMENT.ECU_ADDRESS`` is one level deeper -
	an ``EcuAddressType`` wrapping its own ``Address`` (``LongType``) field.

	Args:
		message (Message): The parent message (e.g. a ``MeasurementType``).
		field_name (str): Name of the ``EcuAddressType`` field on ``message``.

	Returns:
		str: The address as ``"0x...."``, or ``""`` if the field is absent.
	"""
	if not message.HasField(field_name):
		return ""

	return _address(getattr(message, field_name), "Address")


class A2LViewer(QMainWindow, Ui_A2LViewer):
	"""Standalone window for parsing an A2L (ASAP2) file and browsing its contents.

	Opened via **Tools > A2L Parser** (see :meth:`main.MainWindow.open_a2l_viewer`),
	which reuses a single instance across shows rather than recreating it.
	Parsing itself runs on the GUI thread: unlike :class:`can_viewer.CANViewer`'s
	device I/O, it's a one-shot action triggered by a button press rather than
	a continuous stream, so it follows the same synchronous pattern as
	:class:`elf_viewer.ELFViewer`.
	"""

	def __init__(self, parent = None) -> None:
		"""Builds the window, loads the bundled font, and restores the last-used A2L file.

		Args:
			parent (QWidget, optional): Parent widget for the window.
				Defaults to ``None``.
		"""
		super().__init__(parent)

		self.logger = logging.getLogger(__name__)

		self.setupUi(self)
		# Set icon
		self.setWindowIcon(QIcon(":/logo.png"))

		font = get_global_font()
		if font is not None:
			self.setFont(font)
			self.menuBar().setFont(font)
			self.menuBar().setStyleSheet(f"QMenuBar, QMenu {{ font: {font.pointSize()}pt '{font.family()}'; }}")

		self.action_Load_A2L.triggered.connect(self.load_a2l)
		self.openA2LFileBtn.clicked.connect(self.load_a2l)
		self.parseFileButton.clicked.connect(self.parse_file_btn)
		self.a2lFileLineEdit.textEdited.connect(self.a2lLineEditChanged)

		self.a2l_file = StoredSettings.A2L_FILE.get(None)

		if self.a2l_file is not None:
			self.a2lFileLineEdit.setText(self.a2l_file)

	def load_a2l(self):
		"""Opens a file picker for choosing an A2L file and loads it into the line edit.

		The chosen path is persisted to :data:`StoredSettings.A2L_FILE`.
		No-op if the dialog is cancelled. Doesn't parse the file itself -
		that only happens once **Parse** is pressed (see :meth:`parse_file_btn`).
		"""
		a2l_file, _ = QFileDialog.getOpenFileName(
			self,
			"Open File",
			StoredSettings.A2L_FILE.get(StoredSettings.get_documents_path()),
			"A2L Files (*.a2l)"
		)

		if not a2l_file:
			return

		self.a2l_file = a2l_file
		StoredSettings.A2L_FILE.set(self.a2l_file)
		self.a2lFileLineEdit.setText(self.a2l_file)
		self.statusBar().showMessage("Succesfully loaded A2L file", 5000)

	def a2lLineEditChanged(self):
		"""Persists a manually-typed, currently-valid A2L path as it's edited."""
		text = self.a2lFileLineEdit.text()
		if os.path.isfile(text):
			self.a2l_file = text
			StoredSettings.A2L_FILE.set(self.a2l_file)

	def parse_file_btn(self):
		"""Parses the selected A2L file and rebuilds the tree from its contents.

		Runs the pya2l gRPC-backed parser synchronously on the GUI thread -
		parsing is a one-shot action triggered by this button, not a
		continuous stream, so there's no separate worker thread involved (see
		the class docstring). A failure to parse (missing file, malformed
		A2L, backend error) is reported via a message box rather than raising,
		and leaves the tree untouched.
		"""
		if not self.a2l_file or not os.path.isfile(self.a2l_file):
			QMessageBox.critical(self, "A2L Error", f"A2L file not found: {self.a2l_file}")
			self.statusBar().showMessage("Failed to parse A2L file...", 10000)
			return

		with open(self.a2l_file, "rb") as f:
			data = f.read()

		# A2L files exported by common calibration tools (e.g. ETAS INCA,
		# Vector CANape) are often saved as UTF-8 with a BOM. pya2l's grammar
		# doesn't skip it, so it shows up as a spurious "token recognition
		# error at: ''" for line 1 alongside any real errors in the file.
		data = data.removeprefix(b"\xef\xbb\xbf")
		# See _strip_if_data_blocks: works around a pya2l grammar bug where
		# an ASAP2 keyword used as a bare value inside IF_DATA's vendor
		# content aborts parsing of the whole file.
		data = _strip_if_data_blocks(data)
		# See _quote_bare_format_specs: works around tools that export
		# FORMAT's printf spec without the quotes the grammar requires.
		data = _quote_bare_format_specs(data)
		# See _pad_short_matrix_dims: works around pya2l hardcoding
		# MATRIX_DIM at exactly 3 dimensions.
		data = _pad_short_matrix_dims(data)

		try:
			# The parser owns a local gRPC server for the duration of the
			# `with` block; scoping it to a single parse rather than keeping
			# it alive for the window's lifetime keeps this window free of
			# any process cleanup on close.
			with A2lParser(logger = self.logger) as parser:
				tree = parser.tree_from_a2l(data)
		except A2lError as e:
			# self.logger.error(f"Failed to parse A2L file:\n{e}")	
			QMessageBox.critical(self, "A2L Error", f"Failed to parse A2L file:\n{e}")
			self.statusBar().showMessage("Failed to parse A2L file...", 10000)
			return

		self.a2lTree.clear()
		for module in tree.PROJECT.MODULE:
			self._populate_module(module)

		self.a2lTree.expandToDepth(0)
		for column in range(self.a2lTree.columnCount()):
			self.a2lTree.resizeColumnToContents(column)

	def _populate_module(self, module: ModuleType) -> None:
		"""Adds one top-level tree item per A2L category found in ``module``.

		Only categories that actually contain entries get a row, so a module
		that e.g. defines no ``AXIS_PTS`` doesn't clutter the tree with an
		empty "Axis Points" node.

		Args:
			module (ModuleType): A single ``MODULE`` block from the parsed
				A2L's ``PROJECT``.
		"""
		module_item = QTreeWidgetItem(self.a2lTree, [_wrapped(module, "Name"), "MODULE", "", _wrapped(module, "LongIdentifier")])

		categories = (
			("Measurements", module.MEASUREMENT, self._measurement_row),
			("Characteristics", module.CHARACTERISTIC, self._characteristic_row),
			("Compu Methods", module.COMPU_METHOD, self._compu_method_row),
			("Functions", module.FUNCTION, self._function_row),
			("Groups", module.GROUP, self._group_row),
			("Axis Points", module.AXIS_PTS, self._axis_pts_row),
			("Record Layouts", module.RECORD_LAYOUT, self._record_layout_row),
			("Units", module.UNIT, self._unit_row),
		)

		for label, entries, row_fn in categories:
			if len(entries) == 0:
				continue

			category_item = QTreeWidgetItem(module_item, [f"{label} ({len(entries)})", "", "", ""])
			for entry in entries:
				QTreeWidgetItem(category_item, row_fn(entry))

	@staticmethod
	def _measurement_row(measurement) -> list[str]:
		"""Builds a tree row (Name/Type/Address/Description) for one ``MEASUREMENT``."""
		return [
			_wrapped(measurement, "Name"),
			_wrapped(measurement, "DataType"),
			_ecu_address(measurement, "ECU_ADDRESS"),
			_wrapped(measurement, "LongIdentifier"),
		]

	@staticmethod
	def _characteristic_row(characteristic) -> list[str]:
		"""Builds a tree row (Name/Type/Address/Description) for one ``CHARACTERISTIC``.

		Unlike most A2L name/description fields, ``Type`` (VALUE, CURVE,
		MAP, ...) isn't wrapper-typed, so it's read directly.
		"""
		return [
			_wrapped(characteristic, "Name"),
			characteristic.Type,
			_address(characteristic, "Address"),
			_wrapped(characteristic, "LongIdentifier"),
		]

	@staticmethod
	def _compu_method_row(compu_method) -> list[str]:
		"""Builds a tree row (Name/Type/Unit/Description) for one ``COMPU_METHOD``."""
		return [
			_wrapped(compu_method, "Name"),
			compu_method.ConversionType,
			_wrapped(compu_method, "Unit"),
			_wrapped(compu_method, "LongIdentifier"),
		]

	@staticmethod
	def _function_row(function) -> list[str]:
		"""Builds a tree row (Name/Description) for one ``FUNCTION``."""
		return [_wrapped(function, "Name"), "", "", _wrapped(function, "LongIdentifier")]

	@staticmethod
	def _group_row(group) -> list[str]:
		"""Builds a tree row (Name/Description) for one ``GROUP``.

		``GROUP`` names its name/description fields ``GroupName``/
		``GroupLongIdentifier`` rather than the usual ``Name``/``LongIdentifier``.
		"""
		return [_wrapped(group, "GroupName"), "", "", _wrapped(group, "GroupLongIdentifier")]

	@staticmethod
	def _axis_pts_row(axis_pts) -> list[str]:
		"""Builds a tree row (Name/Address/Description) for one ``AXIS_PTS``."""
		return [
			_wrapped(axis_pts, "Name"),
			"",
			_address(axis_pts, "Address"),
			_wrapped(axis_pts, "LongIdentifier"),
		]

	@staticmethod
	def _record_layout_row(record_layout) -> list[str]:
		"""Builds a tree row (Name only) for one ``RECORD_LAYOUT``.

		``RECORD_LAYOUT`` has no ``LongIdentifier`` field to show.
		"""
		return [_wrapped(record_layout, "Name"), "", "", ""]

	@staticmethod
	def _unit_row(unit) -> list[str]:
		"""Builds a tree row (Name/Type/Display/Description) for one ``UNIT``."""
		return [
			_wrapped(unit, "Name"),
			unit.Type,
			_wrapped(unit, "Display"),
			_wrapped(unit, "LongIdentifier"),
		]
