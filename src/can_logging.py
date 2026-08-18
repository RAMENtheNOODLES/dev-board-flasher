from typing import overload, Optional

from PySide6.QtWidgets import QTreeView, QWidget, QAbstractItemView, QStyledItemDelegate
from PySide6.QtGui import QStandardItem, QStandardItemModel, QPen
from PySide6.QtCore import Qt, QTimer, QModelIndex
from canlib.frame import Frame

import logging

# VALUE/UNIT (columns 6-7) are left unlabeled in the real header since they're
# meaningless for a message row - only its signal children use them. Each
# message instead gets its own fake "sub-header" row labeling them; see
# _populate_signal_children().
_CAN_HEADER = ["MESSAGE", "CHANNEL", "DLC", "DATA", "TIME", "DELTA", "", ""]
_VALUE_COLUMN = 6
_UNIT_COLUMN = 7


class _ColumnSeparatorDelegate(QStyledItemDelegate):
	"""Draws a vertical separator on the right edge of each cell.

	QTreeView has no built-in showGrid like QTableView. A QSS
	``border-right`` could fake one, but applying any stylesheet to the
	view makes Qt's style-sheet engine paint item text with the
	application's default font instead of the custom one CANViewer
	installs, so the line is drawn by hand here instead.
	"""

	def paint(self, painter, option, index):
		super().paint(painter, option, index)
		painter.save()
		painter.setPen(QPen(option.palette.mid().color()))
		painter.drawLine(option.rect.topRight(), option.rect.bottomRight())
		painter.restore()


class CanLogging(QTreeView):
	"""Tree view listing a loaded DBC's messages/signals, used by :class:`can_viewer.CANViewer`."""

	def __init__(self, parent: QWidget | None) -> None:
		super().__init__(parent)
		self.root_node: QStandardItem|None = None
		self.nodes: dict[int, QStandardItem] = {}
		self.out: dict[int, tuple[str, list[tuple[str, str]]]] = {}
		# Driver timestamp (ms) of the last frame seen for each message id, used
		# to compute the DELTA column.
		self.last_seen: dict[int, int] = {}
		# Number of rows, at the top of the tree, for message ids seen on the
		# bus but not present in the loaded DBC. Kept so each newly-seen
		# unknown id can be inserted right after the previous one and still
		# stay above every DBC-known message.
		self.unknown_count = 0
		# msg_ids whose signal children have already been built, so a
		# message only gets its signal rows added the first time it's
		# actually seen on the bus - DBC messages that never show up stay
		# collapsed leaves instead of cluttering the tree with rows that
		# will never have data.
		self.populated_children: set[int] = set()
		self.logger = logging.getLogger(__name__)
		self.mainModel = QStandardItemModel()
		self.mainModel.setHorizontalHeaderLabels(_CAN_HEADER)
		self.setModel(self.mainModel)

		self.setAlternatingRowColors(True)
		self.setItemDelegate(_ColumnSeparatorDelegate(self))
		self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

		# _resize_columns() is fairly expensive (it expands every row to
		# measure collapsed children). update_tree() runs once per received
		# frame, which at real bus rates is way too often to resize on
		# directly, so those calls instead go through this timer to cap it
		# at 4 resizes/second regardless of frame rate.
		self._resize_timer = QTimer(self)
		self._resize_timer.setSingleShot(True)
		self._resize_timer.setInterval(250)
		self._resize_timer.timeout.connect(self._resize_columns)

	def populate_tree(self, dbc_data: dict[int, tuple[str, list[tuple[str, str]]]]):
		"""Build the message/signal tree from already-extracted DBC data.

		``dbc_data`` is expected to come from ``CAN.dbc_message_signals()``,
		gathered off the GUI thread (see ``CanWorker``) since walking a DBC
		file's messages/signals is too slow to do inline in a UI handler.
		Runs again on every reconnect, so any rows from a previous connection
		are cleared first rather than left to accumulate as duplicates.

		Only the top-level message rows are built here; a message's signal
		children are added lazily by :meth:`update_tree` the first time that
		message is actually received; see :meth:`_populate_signal_children`.
		Every row starts hidden - :meth:`update_tree` unhides a message the
		first time it's actually seen, so the tree doesn't list hundreds of
		DBC messages that never show up on the bus.
		"""
		self.clear_tree()
		self.mainModel.setHorizontalHeaderLabels(_CAN_HEADER)

		self.root_node = self.mainModel.invisibleRootItem()

		self.nodes = {}
		self.out = dbc_data
		self.last_seen = {}
		self.unknown_count = 0
		self.populated_children = set()

		for msg_id, (msg_name, _) in dbc_data.items():
			new_node = QStandardItem(msg_name)
			self.nodes[msg_id] = new_node
			self.root_node.appendRow(new_node)
			self.setRowHidden(new_node.row(), QModelIndex(), True)

		self._resize_columns()

		self.logger.debug(f"DBC Messages found: {self.out}")

	def _populate_signal_children(self, node: QStandardItem, signals: list[tuple[str, str]]) -> None:
		"""Adds a message node's signal rows, filling in each one's UNIT column.

		The real header leaves VALUE/UNIT unlabeled (see `_CAN_HEADER`), so
		the first child here is a bold, unselectable row labeling them
		instead - a fake "sub-header" that only appears once a message
		actually has signal rows to label.
		"""
		header_row = QStandardItem("")
		value_header = QStandardItem("VALUE")
		unit_header = QStandardItem("UNIT")
		for item in (header_row, value_header, unit_header):
			item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
			font = item.font()
			font.setBold(True)
			item.setFont(font)

		node.appendRow(header_row)
		node.setChild(0, _VALUE_COLUMN, value_header)
		node.setChild(0, _UNIT_COLUMN, unit_header)

		for signal_name, unit in signals:
			node.appendRow(QStandardItem(signal_name))
			if unit:
				node.setChild(node.rowCount() - 1, _UNIT_COLUMN, QStandardItem(unit))

	def update_tree(self, frame: Frame, channel: int, decoded: Optional[dict[str, object]] = None) -> None:
		"""Updates the tree row for a received frame.

		Called from :meth:`can_viewer.CANViewer._on_frame_received` for every
		received frame. Frames matching a message populated by
		:meth:`populate_tree` have their CHANNEL/DLC/DATA/TIME/DELTA columns
		refreshed in place; unrecognized ids get a new top-level node so they
		still show up in the tree. A DBC-known message gets its signal
		children built and its row unhidden the first time it's seen here,
		rather than upfront in :meth:`populate_tree`, so messages that never
		actually appear on the bus don't clutter the tree at all. ``decoded``
		(from `CAN.decode`), if given, also fills in each matching signal
		child's VALUE column.
		"""
		if self.root_node is None:
			self.root_node = self.mainModel.invisibleRootItem()

		msg_id = frame.id
		node = self.nodes.get(msg_id)
		if node is None:
			self.logger.debug(f"New message id seen on bus: 0x{msg_id:X}")
			node = QStandardItem(f"0x{msg_id:X}")
			# Goes above the DBC-known messages rather than at the end.
			self.root_node.insertRow(self.unknown_count, node)
			self.unknown_count += 1
			self.nodes[msg_id] = node
		elif msg_id in self.out and msg_id not in self.populated_children:
			_, signals = self.out[msg_id]
			self._populate_signal_children(node, signals)
			self.populated_children.add(msg_id)

		last_timestamp = self.last_seen.get(msg_id)
		delta = "" if last_timestamp is None or frame.timestamp is None else f"{frame.timestamp - last_timestamp} ms"
		if frame.timestamp is not None:
			self.last_seen[msg_id] = frame.timestamp

		row = node.row()
		self.setRowHidden(row, QModelIndex(), False)
		self.mainModel.setItem(row, 1, QStandardItem(str(channel)))
		self.mainModel.setItem(row, 2, QStandardItem(str(frame.dlc)))
		self.mainModel.setItem(row, 3, QStandardItem(frame.data.hex(" ")))
		self.mainModel.setItem(row, 4, QStandardItem("" if frame.timestamp is None else f"{frame.timestamp} ms"))
		self.mainModel.setItem(row, 5, QStandardItem(delta))

		if decoded is not None:
			for child_row in range(node.rowCount()):
				signal_item = node.child(child_row, 0)
				if signal_item is None:
					continue
				value = decoded.get(signal_item.text())
				if value is not None:
					node.setChild(child_row, _VALUE_COLUMN, QStandardItem(str(value)))

		if not self._resize_timer.isActive():
			self._resize_timer.start()

	def _resize_columns(self) -> None:
		"""Resizes every column to fit its contents, including collapsed children.

		``resizeColumnToContents()`` only measures currently visible rows, so
		a collapsed message's signal names wouldn't otherwise count toward
		the MESSAGE column's width. Expanding everything first makes it see
		them too; each row's prior expand state is restored afterwards so
		this doesn't fight the user for control of the tree, and updates are
		suppressed so the temporary expansion never gets painted.
		"""
		expanded = [self.isExpanded(self.mainModel.index(row, 0)) for row in range(self.mainModel.rowCount())]

		self.setUpdatesEnabled(False)
		try:
			self.expandAll()
			for column in range(self.mainModel.columnCount()):
				self.resizeColumnToContents(column)
			for row, was_expanded in enumerate(expanded):
				self.setExpanded(self.mainModel.index(row, 0), was_expanded)
		finally:
			self.setUpdatesEnabled(True)

	def clear_tree(self):
		"""Removes all message/signal nodes populated by :meth:`populate_tree`."""
		if self.root_node is not None:
			self.root_node.removeRows(0, len(self.nodes))
