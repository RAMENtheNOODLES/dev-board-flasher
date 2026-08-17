from typing import overload

from PySide6.QtWidgets import QTreeView, QWidget, QAbstractItemView
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtCore import Qt

import logging

_CAN_HEADER = ["MESSAGE", "CHANNEL", "DLC", "DATA", "TIME", "DELTA"]

class CanLogging(QTreeView):
	"""Tree view listing a loaded DBC's messages/signals, used by :class:`can_viewer.CANViewer`."""

	def __init__(self, parent: QWidget | None) -> None:
		super().__init__(parent)
		self.root_node: QStandardItem|None = None
		self.nodes: dict[int, QStandardItem] = {}
		self.out: dict[int, tuple[str, list[str]]] = {}
		self.logger = logging.getLogger(__name__)
		self.mainModel = QStandardItemModel()
		self.mainModel.setHorizontalHeaderLabels(_CAN_HEADER)
		self.setModel(self.mainModel)

	def populate_tree(self, dbc_data: dict[int, tuple[str, list[str]]]):
		"""Build the message/signal tree from already-extracted DBC data.

		``dbc_data`` is expected to come from ``CAN.dbc_message_signals()``,
		gathered off the GUI thread (see ``CanWorker``) since walking a DBC
		file's messages/signals is too slow to do inline in a UI handler.
		"""
		self.root_node = self.mainModel.invisibleRootItem()

		self.nodes = {}
		self.out = dbc_data

		for msg_id, (msg_name, signal_names) in dbc_data.items():
			new_node = QStandardItem(msg_name)

			for signal in signal_names:
				new_node.appendRow(QStandardItem(signal))

			self.nodes[msg_id] = new_node
			self.root_node.appendRow(new_node)

		self.logger.debug(f"DBC Messages found: {self.out}")

	def update_tree(self, msg_id: int) -> None:
		"""Notes that a frame for ``msg_id`` was received, if it has a matching tree node.

		Called from :meth:`can_viewer.CANViewer._on_frame_received` for every
		received frame. Currently only logs whether ``msg_id`` matches a node
		populated by :meth:`populate_tree`; the tree's DLC/DATA/TIME/DELTA
		columns aren't updated yet.
		"""
		if self.out.__contains__(msg_id):
			self.logger.debug(f"Nodes: {self.nodes[msg_id]}")
		else:
			self.logger.debug(f"Does not contain {msg_id}")

	def clear_tree(self):
		"""Removes all message/signal nodes populated by :meth:`populate_tree`."""
		if self.root_node is not None:
			self.root_node.removeRows(0, len(self.nodes))
