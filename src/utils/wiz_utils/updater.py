import logging
import os

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import QMessageBox

from . import (
	apply_update,
	check_for_updates,
	download_update,
	find_asset,
)


class Updater(QThread):
	"""Checks for and installs app updates, downloading the new release on a background thread.

	:meth:`check_for_updates_and_install` runs the check and (if accepted)
	kicks off the download by starting this thread's :meth:`run`; the actual
	install (silently running the downloaded installer, which closes and
	relaunches this app) happens on the GUI thread once :meth:`run` reports
	back via ``finished_ok``.
	"""

	progress = Signal(float)  # download progress, 0-1
	finished_ok = Signal(str)   # path to downloaded file
	failed = Signal(str)		# error message

	def __init__(self) -> None:
		"""Connects ``finished_ok``/``failed`` to their install/error handlers."""
		super().__init__()
		self.logger = logging.getLogger(__name__)
		self.finished_ok.connect(self._on_download_finished)
		self.failed.connect(self._on_download_failed)

	def check_for_updates_and_install(self, force_update: bool = False) -> bool:
		"""Checks GitHub for a newer release and, if one exists, prompts the user to install it.

		When running from source, installing isn't supported (see
		:func:`apply_update`, which runs the downloaded installer against
		the packaged app's install directory), so the user is only notified
		a newer version exists rather than prompted to install it. When a
		compiled build accepts the prompt, the download/install itself
		happens asynchronously on this ``QThread`` (started here, finishing
		via :meth:`_on_download_finished`).

		Returns:
			bool: ``True`` if an update was available (regardless of
				whether the user chose to install it, or whether install is
				even supported in this run mode), ``False`` if already on
				the latest version.
		"""
		can_update, latest_version, resp = check_for_updates(force_update)

		if (can_update and not force_update) and "__compiled__" not in globals():
			# Running from source: apply_update() launches the installer
			# against the packaged app's install directory, which doesn't
			# exist in a dev checkout. Self-update is only safe for
			# packaged (Nuitka-compiled) builds.
			self.logger.warning(f"Update {latest_version} available, but self-update is disabled in dev mode.")
			msg = QMessageBox()
			msg.setIcon(QMessageBox.Icon.Information)
			msg.setWindowTitle("Update App")
			msg.setText(f"A new version is available ({latest_version}), but self-update isn't supported when running from source. Please pull the latest changes instead.")
			msg.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
			msg.exec()
			return True

		if can_update or force_update:
			msg = QMessageBox(			
				QMessageBox.Icon.Information,
				"Update App",
				f"A new version is available ({latest_version}), would you like to update?",
				QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
				None, Qt.WindowType.WindowStaysOnTopHint
			)

			msg.setDefaultButton(QMessageBox.StandardButton.No)

			result = msg.exec()

			if result == QMessageBox.StandardButton.Yes:
				self.logger.info("Updating app...")
				asset = find_asset(resp, f"dev-board-flasher-{latest_version}-setup.exe")
				if asset is None:
					self.logger.error(f"Expected asset not found in latest release ({latest_version})")
					err = QMessageBox()
					err.setIcon(QMessageBox.Icon.Warning)
					err.setWindowTitle("Update App")
					err.setText(f"Couldn't find a downloadable update for version {latest_version}. Please download it manually from the GitHub releases page.")
					err.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
					err.exec()
					return True

				self.url = asset["browser_download_url"]
				self.dest_path = os.path.join(os.environ["TEMP"], "dev-board-flasher-setup.exe")

				# Extraction/install happens in _on_download_finished once run()
				# completes the download on the background thread.
				self.start()

			return True
		else:
			return False

	def run(self):
		"""Downloads the update to ``self.dest_path``, set beforehand by :meth:`check_for_updates_and_install`.

		Emits ``progress`` as the download proceeds, then ``finished_ok`` on
		success or ``failed`` with the error message on failure. Runs on this
		``QThread``, not the GUI thread.
		"""
		try:
			download_update(self.url, self.dest_path, on_progress=self.progress.emit)
			self.finished_ok.emit(self.dest_path)
		except Exception as e:  # noqa: BLE001 - reported via `failed` instead of crashing this QThread
			self.failed.emit(str(e))

	def _on_download_finished(self, dest_path: str) -> None:
		"""Extracts the downloaded zip and hands off to :func:`apply_update`. Connected to ``finished_ok``.

		Args:
			dest_path (str): Path of the downloaded update zip.
		"""
		try:
			self.logger.info(f"Applying update: {dest_path!r}")

			apply_update(dest_path)
		except Exception as e:  # noqa: BLE001 - install best-effort; log and move on rather than crash
			self.logger.error(f"Failed to apply update: {e}")

	def _on_download_failed(self, error: str) -> None:
		"""Logs a failed download. Connected to ``failed``.

		Args:
			error (str): Description of what went wrong.
		"""
		self.logger.error(f"Update download failed: {error}")