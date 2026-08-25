from PySide6.QtWidgets import QDialog, QFileDialog, QMessageBox

from tools.j1939_dm1 import load_fmi_names, load_spn_names
from ui_can_j1939_dm1 import Ui_Dialog
from utils.wiz_utils.stored_settings import StoredSettings


class J1939ConfigDialog(QDialog):
	"""Modal dialog (**CAN Viewer > File > Configure J1939**) for picking the DM1 SPN/FMI name-lookup CSVs.

	Each field is optional and independent - leaving one blank just means
	DTC rows won't show a name for that part of the code, same as never
	opening this dialog at all. See `tools.j1939_dm1.load_spn_names`/
	`load_fmi_names` for the expected CSV format.
	"""

	def __init__(self, parent=None):
		"""Builds the dialog, pre-filling both fields with the previously persisted CSV paths, if any."""
		super().__init__(parent)

		self.ui = Ui_Dialog()
		self.ui.setupUi(self)

		#: Populated on :meth:`accept`; `{}` for any field left blank.
		self.spn_names: dict[int, str] = {}
		self.fmi_names: dict[int, str] = {}

		spn_file = StoredSettings.CAN_DM1_SPN_FILE.get(None)
		if spn_file:
			self.ui.dM1SPNLineEdit.setText(spn_file)

		fmi_file = StoredSettings.CAN_DM1_FMI_FILE.get(None)
		if fmi_file:
			self.ui.dM1FMILineEdit.setText(fmi_file)

		self.ui.openSPNFile.clicked.connect(self._browse_spn_file)
		self.ui.openFMIFile.clicked.connect(self._browse_fmi_file)

	def _browse_spn_file(self) -> None:
		path, _ = QFileDialog.getOpenFileName(
			self, "Open SPN Name CSV", StoredSettings.get_documents_path(), "CSV Files (*.csv);; All Files (*)"
		)
		if path:
			self.ui.dM1SPNLineEdit.setText(path)

	def _browse_fmi_file(self) -> None:
		path, _ = QFileDialog.getOpenFileName(
			self, "Open FMI Name CSV", StoredSettings.get_documents_path(), "CSV Files (*.csv);; All Files (*)"
		)
		if path:
			self.ui.dM1FMILineEdit.setText(path)

	def accept(self) -> None:
		"""Loads whichever fields aren't blank, closing the dialog only if both succeed.

		A non-blank field that fails to load (missing file or malformed
		CSV) shows an error and leaves the dialog open instead, so the user
		can fix or clear it rather than silently losing the other field's
		choice.
		"""
		spn_path = self.ui.dM1SPNLineEdit.text().strip()
		fmi_path = self.ui.dM1FMILineEdit.text().strip()

		try:
			spn_names = load_spn_names(spn_path) if spn_path else {}
			fmi_names = load_fmi_names(fmi_path) if fmi_path else {}
		except (OSError, ValueError) as e:
			QMessageBox.critical(self, "Failed to Load CSV", str(e))
			return

		self.spn_names = spn_names
		self.fmi_names = fmi_names
		StoredSettings.CAN_DM1_SPN_FILE.set(spn_path)
		StoredSettings.CAN_DM1_FMI_FILE.set(fmi_path)

		super().accept()
