from . import download_update, check_for_updates, find_asset, apply_update, get_current_exe_path
from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QMessageBox
import zipfile, os, sys
import logging

class Updater(QThread):
	progress = Signal(float)
	finished_ok = Signal(str)   # path to downloaded file
	failed = Signal(str)		# error message

	def __init__(self) -> None:
		super().__init__()
		self.logger = logging.getLogger(__name__)
		self.finished_ok.connect(self._on_download_finished)
		self.failed.connect(self._on_download_failed)

	@staticmethod
	def extract_zip(zip_path: str, extract_dir: str) -> str:
		"""Extracts the zip and returns the path to the .exe inside it."""
		with zipfile.ZipFile(zip_path, "r") as z:
			z.extractall(extract_dir)
			# find the exe inside — adjust if you know the exact name/structure
			exe_names = [n for n in z.namelist() if n.lower().endswith(".exe")]
			if not exe_names:
				raise RuntimeError("No .exe found in downloaded zip")
			return os.path.join(extract_dir, exe_names[0])

	def check_for_updates_and_install(self):
		can_update, latest_version, resp = check_for_updates()

		if can_update and "__compiled__" not in globals():
			# Running from source: get_current_exe_path() would resolve to
			# main.py, and apply_update() would overwrite it. Self-update is
			# only safe for packaged (Nuitka-compiled) builds.
			self.logger.warning(f"Update {latest_version} available, but self-update is disabled in dev mode.")
			QMessageBox.information(
				None,
				"Update App",
				f"A new version is available ({latest_version}), but self-update isn't supported when running from source. Please pull the latest changes instead."
			)
			return

		if can_update:
			result = QMessageBox.question(
				None,
				"Update App",
				f"A new version is available ({latest_version}), would you like to update?",
				QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
				QMessageBox.StandardButton.No
			)

			if result == QMessageBox.StandardButton.Yes:
				self.logger.info("Updating app...")
				asset = find_asset(resp, f"dev-board-flasher-{latest_version}-windows.zip")
				if asset is None:
					raise RuntimeError("Expected asset not found in latest release")

				self.url = asset["browser_download_url"]
				self.dest_path = os.path.join(os.environ["TEMP"], "dev-board-flasher.zip")

				# Extraction/install happens in _on_download_finished once run()
				# completes the download on the background thread.
				self.start()

	def run(self):
		try:
			download_update(self.url, self.dest_path, on_progress=self.progress.emit)
			self.finished_ok.emit(self.dest_path)
		except Exception as e:
			self.failed.emit(str(e))

	def _on_download_finished(self, dest_path: str) -> None:
		try:
			extract_dir = os.path.join(os.environ["TEMP"], "wiz_utils_update")
			os.makedirs(extract_dir, exist_ok=True)
			new_exe_path = self.extract_zip(dest_path, extract_dir)
			current_exe_path = get_current_exe_path()

			self.logger.info(f"Applying update: {new_exe_path!r} -> {current_exe_path!r} (sys.executable={sys.executable!r})")

			apply_update(new_exe_path, current_exe_path)
		except Exception as e:
			self.logger.error(f"Failed to apply update: {e}")

	def _on_download_failed(self, error: str) -> None:
		self.logger.error(f"Update download failed: {error}")