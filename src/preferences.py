import logging

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QDialog, QFileDialog, QMessageBox

from ui_preferences import Ui_PreferencesWindow
from utils.ui_utils import get_global_font
from utils.wiz_utils import reload_app
from utils.wiz_utils.stored_settings import StoredSettings


class Preferences(QDialog, Ui_PreferencesWindow):
	"""Modal dialog for **Edit > Preferences...**: app font override plus settings backup/import/export/reset.

	**General** holds the font override (see :meth:`reset`,
	:meth:`save_settings_btn`, :meth:`reset_to_defaults_btn`); **Advanced**
	holds whole-settings-file import/export (:meth:`import_settings_btn`,
	:meth:`export_settings_btn`) and :meth:`clear_all_settings_btn`.
	"""

	def __init__(self, parent=None):
		"""Builds the dialog, wires up its buttons, then applies the current global font via :meth:`reset`.

		Args:
			parent (QWidget, optional): Parent widget, passed through to
				:class:`~PySide6.QtWidgets.QDialog`.
		"""
		super().__init__(parent)
		self.logger = logging.getLogger(__name__)
		self.setupUi(self)

		self.clearAllSettingsBtn.clicked.connect(self.clear_all_settings_btn)
		self.fontComboBox.currentFontChanged.connect(self.update_font)
		self.saveSettingsBtn.clicked.connect(self.save_settings_btn)
		self.defaultsBtn.clicked.connect(self.reset_to_defaults_btn)
		self.importSettingsBtn.clicked.connect(self.import_settings_btn)
		self.exportSettingsBtn.clicked.connect(self.export_settings_btn)
		self.fontSizeBox.valueChanged.connect(self.font_size_changed)

		self.reset()

	def reset(self):
		"""Refreshes the dialog to reflect the currently stored font/size, discarding any unsaved combo/spin box change.

		Applies :func:`utils.ui_utils.get_global_font` to the dialog itself
		(so the **General** tab always previews the font that's actually
		stored, not a stale one from before a reload), syncs the font combo
		box and font size spin box to match, and resets :attr:`chosenFont`/
		:attr:`chosenFontSize` to it. Called once from :meth:`__init__` and
		again from :meth:`reset_to_defaults_btn` after
		:data:`StoredSettings.APP_FONT`/:data:`StoredSettings.APP_FONT_SIZE`
		are cleared.
		"""
		font = get_global_font()
		if font is not None:
			self.setFont(font)

		self.fontComboBox.setCurrentFont(self.font())
		self.chosenFont = self.font()
		font_size = self.font().pointSize()
		self.chosenFontSize = font_size
		self.fontSizeBox.setValue(font_size)
		self.unsaved = False

	def export_settings_btn(self):
		"""Handles **Export Settings**: prompts for a destination file, then writes every stored setting to it.

		A no-op if the save dialog is cancelled. See
		:meth:`StoredSettings.export_settings`.
		"""
		settings_loc, _ = QFileDialog.getSaveFileName(
			self,
			"Save File",
			StoredSettings.get_documents_path(),
			"Config Files (*.ini);; All Files (*)"
		)

		if settings_loc:
			StoredSettings.export_settings(settings_loc)

	def import_settings_btn(self):
		"""Handles **Import Settings**: prompts for a source file, then replaces every stored setting with its contents.

		A no-op if the open dialog is cancelled. On a successful import, asks
		whether to reload the app now: accepting calls :func:`utils.wiz_utils.reload_app`
		immediately (skipping the refresh below, since the app is about to
		restart anyway); declining instead calls :meth:`reset` so the dialog
		itself reflects the imported font/size right away. See
		:meth:`StoredSettings.import_settings`.
		"""
		settings_loc, _ = QFileDialog.getOpenFileName(
			self,
			"Open File",
			StoredSettings.get_documents_path(),
			"Config Files (*.ini);; All Files (*)"
		)

		if settings_loc:
			StoredSettings.import_settings(settings_loc)

			result = QMessageBox.question(
				self, 
				"Reload App?", 
				"Would you like to reload the app to apply the new settings?",
				QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
				QMessageBox.StandardButton.Yes
			)

			if result == QMessageBox.StandardButton.Yes:
				reload_app()
				return

			self.reset()

	def update_font(self, font: QFont):
		"""Tracks the font picked in the font combo box, staging it for :meth:`save_settings_btn`."""
		self.chosenFont = font

	def font_size_changed(self, font_size: int):
		"""Tracks the size picked in the font size spin box, staging it for :meth:`save_settings_btn`."""
		self.chosenFontSize = font_size

	def save_settings_btn(self):
		"""Handles **Save Settings**: persists the chosen font/size to :data:`StoredSettings.APP_FONT`/:data:`StoredSettings.APP_FONT_SIZE`.

		The new font isn't applied to the running app, since it's only read
		back the next time :func:`utils.ui_utils.get_global_font` runs (i.e.
		on the next launch/reload), so the user is prompted to restart.
		"""
		StoredSettings.APP_FONT.set(self.chosenFont)
		StoredSettings.APP_FONT_SIZE.set(self.chosenFontSize)
		QMessageBox.information(self, "", "Please reload the app for the font changes to take affect...")

	def reset_to_defaults_btn(self):
		"""Handles **Revert to Defaults**: confirms, then clears the ``preferences`` settings group and refreshes the dialog.

		Currently only :data:`StoredSettings.APP_FONT` lives in that group,
		so this is equivalent to clearing the font override; unlike
		:meth:`clear_all_settings_btn`, other settings (selected board,
		remote configs, etc.) are untouched. See
		:meth:`StoredSettings.clear_settings_in_group`.
		"""
		resp = QMessageBox.critical(
			self, 
			"Confirm", 
			"Are you sure you want to reset preferences to default values?",
			QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
			QMessageBox.StandardButton.Cancel
		)
		
		if resp == QMessageBox.StandardButton.Yes:
			StoredSettings.clear_settings_in_group("preferences")
			self.reset()

	def clear_all_settings_btn(self):
		"""Handles **Clear All Settings**: confirms, then wipes every stored setting.

		Doesn't restart the app, since the wiped values are only re-read the
		next time each is fetched (e.g. next launch), not held in memory.
		"""
		resp = QMessageBox.critical(
			self, 
			"Confirm", 
			"Are you sure you want to clear ALL settings?",
			QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
			QMessageBox.StandardButton.Cancel
		)

		if resp == QMessageBox.StandardButton.Yes:
			StoredSettings.clear_all_settings()