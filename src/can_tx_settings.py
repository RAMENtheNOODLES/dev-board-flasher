from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
	QCheckBox,
	QComboBox,
	QDialog,
	QDoubleSpinBox,
	QFormLayout,
	QHBoxLayout,
	QMessageBox,
	QSpinBox,
	QWidget,
)

from tools.can import CAN, TxMessageConfig, TxMessageInfo, TxSignalInfo
from ui_can_tx_settings import Ui_Dialog
from utils.wiz_utils.tx_scheduler import TxScheduler

_COL_PGN = 0
_COL_RATE = 1
_COL_ENABLED = 2
_COL_SIGNALS = 3

_DEFAULT_RATE_MS = 1000
_MIN_RATE_MS = 10
_MAX_RATE_MS = 60_000


class TxSettingsDialog(QDialog):
	"""Modal dialog (**CAN Viewer > File > TX Settings**) for configuring periodically-transmitted DBC messages.

	Each row of `txMessages` picks a DBC message (labeled by its J1939 PGN),
	a send rate, whether it's currently active, and an editor for each of
	its signals' values - a dropdown of the DBC's defined labels for a
	signal with a value table (see `_build_signal_editor`), otherwise a
	plain numeric spin box. Accepting applies the whole table to `tx_scheduler`
	in one go, which is what actually starts/stops/retimes the periodic
	sends (see `TxScheduler`); cancelling leaves it untouched. Reopening the
	dialog prefills the table from `tx_scheduler.get_configs()`, so it
	always reflects whatever is currently active rather than starting blank.
	"""

	def __init__(self, can: CAN, tx_scheduler: TxScheduler, parent=None):
		super().__init__(parent)

		self.tx_scheduler = tx_scheduler
		self.messages_by_name: dict[str, TxMessageInfo] = {info.name: info for info in can.dbc_tx_messages()}

		self.ui = Ui_Dialog()
		self.ui.setupUi(self)

		self.ui.txMessages.setColumnCount(4)
		self.ui.txMessages.setHorizontalHeaderLabels(["Message (PGN)", "Rate", "Enabled", "SPNs"])

		# QPushButton.clicked passes a `checked: bool` that _add_row would
		# otherwise receive as its `config` argument - the lambda discards it.
		self.ui.newTxButton.clicked.connect(lambda _checked: self._add_row())
		self.ui.removeTxButton.clicked.connect(self._remove_selected_rows)

		for config in tx_scheduler.get_configs():
			self._add_row(config)

		self._fit_to_contents()

	def _add_row(self, config: TxMessageConfig | None = None) -> None:
		"""Adds a new row, prefilled from `config` if given (a persisted one) or DBC/UI defaults otherwise (a fresh one from the "+" button)."""
		if not self.messages_by_name:
			QMessageBox.warning(self, "No DBC Loaded", "Load a DBC file with messages before adding a TX message.")
			return

		table = self.ui.txMessages
		row = table.rowCount()
		table.insertRow(row)

		pgn_combo = QComboBox()
		for info in self.messages_by_name.values():
			pgn_combo.addItem(f"{info.name} (PGN 0x{info.pgn:04X})", info.name)
		if config is not None:
			index = pgn_combo.findData(config.message_name)
			pgn_combo.setCurrentIndex(max(index, 0))
		table.setCellWidget(row, _COL_PGN, pgn_combo)

		rate_spin = QSpinBox()
		rate_spin.setRange(_MIN_RATE_MS, _MAX_RATE_MS)
		rate_spin.setSuffix(" ms")
		rate_spin.setValue(config.rate_ms if config is not None else _DEFAULT_RATE_MS)
		table.setCellWidget(row, _COL_RATE, rate_spin)

		enabled_check = QCheckBox()
		enabled_check.setChecked(config.enabled if config is not None else False)
		enabled_container = QWidget()
		enabled_layout = QHBoxLayout(enabled_container)
		enabled_layout.setContentsMargins(0, 0, 0, 0)
		enabled_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
		enabled_layout.addWidget(enabled_check)
		table.setCellWidget(row, _COL_ENABLED, enabled_container)

		# Built with the row's initial state before this connects, so
		# setCurrentIndex() above doesn't also trigger it - see
		# _on_pgn_changed for why a later change looks its row up by
		# widget identity rather than capturing the index it had here.
		self._rebuild_signal_editors(row, initial_values=config.signal_values if config is not None else None)
		pgn_combo.currentIndexChanged.connect(lambda _index, combo=pgn_combo: self._on_pgn_changed(combo))

	def _on_pgn_changed(self, pgn_combo: QComboBox) -> None:
		"""Rebuilds a row's SPN editors after its message selection changes, resetting them to that message's DBC defaults."""
		row = self._row_of_widget(pgn_combo, _COL_PGN)
		if row is not None:
			self._rebuild_signal_editors(row)

	def _row_of_widget(self, widget: QWidget, column: int) -> int | None:
		"""Finds `widget`'s current row in `column`, since row removal can shift indices captured earlier."""
		table = self.ui.txMessages
		for row in range(table.rowCount()):
			if table.cellWidget(row, column) is widget:
				return row
		return None

	def _rebuild_signal_editors(self, row: int, initial_values: dict[str, float] | None = None) -> None:
		pgn_combo: QComboBox = self.ui.txMessages.cellWidget(row, _COL_PGN)
		info = self.messages_by_name.get(pgn_combo.currentData())

		container = QWidget()
		form = QFormLayout(container)
		form.setContentsMargins(4, 4, 4, 4)

		editors: dict[str, QDoubleSpinBox | QComboBox] = {}
		if info is not None:
			for signal in info.signals:
				default = (initial_values or {}).get(signal.name, signal.default_value)
				label = f"{signal.name} ({signal.unit})" if signal.unit else signal.name
				editor = self._build_signal_editor(signal, default)
				form.addRow(label, editor)
				editors[signal.name] = editor

		# A plain Python attribute rather than a separate row-keyed dict,
		# since QTableWidget already owns this container at (row, _COL_SIGNALS)
		# and rows can be removed/reordered out from under a row-indexed dict.
		container.editors = editors
		self.ui.txMessages.setCellWidget(row, _COL_SIGNALS, container)
		self.ui.txMessages.setRowHeight(row, container.sizeHint().height())
		self._fit_to_contents()

	@staticmethod
	def _build_signal_editor(signal: TxSignalInfo, default: float) -> QDoubleSpinBox | QComboBox:
		"""Builds one signal's value editor: a combo box of its DBC-defined value-table labels if it has one, else a plain numeric spin box."""
		if signal.enum_values:
			combo = QComboBox()
			for label, raw_value in signal.enum_values.items():
				combo.addItem(label, raw_value)
			index = combo.findData(round(default))
			combo.setCurrentIndex(max(index, 0))
			return combo

		spin = QDoubleSpinBox()
		spin.setRange(-1e9, 1e9)
		spin.setDecimals(3)
		spin.setValue(default)
		return spin

	@staticmethod
	def _editor_value(editor: QDoubleSpinBox | QComboBox) -> float:
		"""Reads back the current value of a signal editor built by `_build_signal_editor`."""
		if isinstance(editor, QComboBox):
			return float(editor.currentData())
		return editor.value()

	def _remove_selected_rows(self) -> None:
		rows = sorted({index.row() for index in self.ui.txMessages.selectedIndexes()}, reverse=True)
		for row in rows:
			self.ui.txMessages.removeRow(row)
		self._fit_to_contents()

	def _fit_to_contents(self) -> None:
		"""Resizes the window to fit the table's current rows/columns, so it never shows blank space or clips a row.

		QTableWidget's own size hint doesn't reflect its full content (it's
		a scroll area, so `adjustSize()` alone wouldn't grow the window to
		fit every row/column, and measuring the table's *current* allocated
		size is circular - it's already clamped to whatever space the
		window happens to have). Giving it a hard minimum size matching its
		actual content instead makes the layout - and so `adjustSize()` -
		account for it properly; that minimum is released again afterward
		if the result would exceed 90% of the current screen's available
		size, so a table with many rows/signals scrolls instead of growing
		the window past the screen.
		"""
		table = self.ui.txMessages
		table.resizeColumnsToContents()
		table.resizeRowsToContents()

		content_width = table.verticalHeader().width() + table.horizontalHeader().length() + 2 * table.frameWidth()
		content_height = table.horizontalHeader().height() + table.verticalHeader().length() + 2 * table.frameWidth()
		table.setMinimumSize(content_width, content_height)
		self.adjustSize()

		screen = self.screen() or QGuiApplication.primaryScreen()
		if screen is None:
			return

		available = screen.availableGeometry()
		max_width = round(available.width() * 0.9)
		max_height = round(available.height() * 0.9)
		if self.width() > max_width or self.height() > max_height:
			# Setting a layout on a top-level widget also keeps that widget's
			# own minimumSize in sync with the layout's, so the larger
			# minimum adjustSize() just grew it to (from the table's) is
			# still in effect here and would otherwise clamp resize() below
			# right back up - both have to be released, and the layout
			# re-activated so a resize to something smaller actually sticks.
			table.setMinimumSize(0, 0)
			self.setMinimumSize(0, 0)
			self.layout().activate()
			self.resize(min(self.width(), max_width), min(self.height(), max_height))

	def accept(self) -> None:
		"""Builds a `TxMessageConfig` per row and applies the whole set to `tx_scheduler` before closing."""
		table = self.ui.txMessages
		configs = []
		for row in range(table.rowCount()):
			pgn_combo: QComboBox = table.cellWidget(row, _COL_PGN)
			message_name = pgn_combo.currentData()
			if message_name is None:
				continue

			rate_spin: QSpinBox = table.cellWidget(row, _COL_RATE)
			enabled_check: QCheckBox = table.cellWidget(row, _COL_ENABLED).findChild(QCheckBox)
			signals_container: QWidget = table.cellWidget(row, _COL_SIGNALS)

			configs.append(TxMessageConfig(
				message_name=message_name,
				rate_ms=rate_spin.value(),
				enabled=enabled_check.isChecked(),
				signal_values={
					name: self._editor_value(editor) for name, editor in signals_container.editors.items()
				},
			))

		self.tx_scheduler.set_configs(configs)
		super().accept()
