from ui_remote_configs import Ui_Dialog
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox, QListWidgetItem, QFileDialog
from PySide6.QtCore import Qt
from utils.wiz_utils.stored_settings import StoredSettings

import logging

class RemoteConfigs(QDialog):
	"""Modal dialog for editing the list of extra board/flashing-tool configs.

	Each row is a local file path or GitHub file URL pointing at a board or
	flashing tool TOML file (loaded in addition to the bundled
	``config/boards``/``config/flashing_tools``). Rows can be typed/edited
	directly, added via a file picker, or removed. The list is only
	persisted to :data:`StoredSettings.REMOTE_CONFIGS` when the dialog is
	accepted (e.g. clicking OK); picking up the change requires restarting
	the app.
	"""

	def __init__(self, parent=None):
		"""Builds the dialog and populates it with the currently stored remote configs.

		Args:
			parent (QWidget, optional): Parent widget for the dialog.
				Defaults to ``None``.
		"""
		super().__init__(parent)

		self.logger = logging.getLogger(__name__)

		self.ui = Ui_Dialog()
		self.ui.setupUi(self)
		self.ui.configsList.itemChanged.connect(self.on_item_edited)
		self.ui.addNewConfigBtn.clicked.connect(self.add_new_item)
		self.ui.browseConfigBtn.clicked.connect(self.browse_files)
		self.ui.removeConfigsBtn.clicked.connect(self.remove_items)

		configs: list[str] = StoredSettings.REMOTE_CONFIGS.get([])

		for config in configs:
			item = QListWidgetItem(config)
			item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
			self.ui.configsList.addItem(item)

	def on_item_edited(self, item):
		"""Logs when a row's text is changed in place.

		Args:
			item (QListWidgetItem): The edited row.
		"""
		self.logger.debug(f"Item updated to: {item.text()}")

	def add_new_item(self):
		"""Adds a blank, immediately-editable row for typing a path or URL."""
		item = QListWidgetItem("New item")
		item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
		self.ui.configsList.addItem(item)
		self.ui.configsList.editItem(item)

	def remove_items(self):
		"""Removes the currently selected row(s) from the list."""
		for item in self.ui.configsList.selectedItems():
			row = self.ui.configsList.row(item)
			self.logger.debug(f"Removing item: {row}")
			removed_item = self.ui.configsList.takeItem(row)
			del removed_item

	def accept(self):
		"""Persists the current list of rows to :data:`StoredSettings.REMOTE_CONFIGS` and closes the dialog."""
		configs_list: list[str] = [self.ui.configsList.item(i).text() for i in range(self.ui.configsList.count())]

		StoredSettings.REMOTE_CONFIGS.set(configs_list)

		super().accept()

	def browse_files(self):
		"""Opens a file picker for adding one or more local TOML config files as rows."""
		config_files, _ = QFileDialog.getOpenFileNames(
			self,
			"Open Files",
			"",
			f"Config Files (*.toml)"
		)

		if len(config_files) > 0:
			for file in config_files:
				item = QListWidgetItem(file)
				item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
				self.ui.configsList.addItem(item)

			self.logger.debug(f"Files ready for upload: {config_files}")