from ui_github_token import Ui_Dialog
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox
from utils.wiz_utils.github_token import GithubToken

class GithubTokenUI(QDialog):
	"""Modal dialog for viewing and setting the stored GitHub personal access token.

	The token is required to fetch board/flashing-tool configs from private
	GitHub repos (see :class:`utils.wiz_utils.github_token.GithubToken`) and
	is stored in the OS credential store rather than app settings.
	"""

	def __init__(self, parent=None):
		"""Builds the dialog, pre-filling the field with the currently stored token, if any.

		Args:
			parent (QWidget, optional): Parent widget for the dialog.
				Defaults to ``None``.
		"""
		super().__init__(parent)

		self.ui = Ui_Dialog()
		self.ui.setupUi(self)
		token = GithubToken.get_token()
		if (token is not None):
			self.ui.accessToken.setText(token)

	def accept(self):
		"""Persists the entered token and closes the dialog, or warns if the field is empty."""
		text = self.ui.accessToken.text()

		if (text != ""):
			GithubToken.set_token(self.ui.accessToken.text())
			super().accept()
		else:
			QMessageBox.warning(
				self,
				"Empty Fields",
				"The access token field is empty!",
				QMessageBox.StandardButton.Ok
			)