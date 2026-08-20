import logging

from PySide6.QtGui import QFont, QFontDatabase

from ..wiz_utils import StoredSettings


def get_global_font() -> QFont|None:
	"""Loads the bundled Nerd Font and returns the app's global font, applying any user overrides.

	Registers the embedded ``FiraCodeNerdFont-Regular.ttf`` resource with
	:class:`~PySide6.QtGui.QFontDatabase`, then builds a default font from
	it at :data:`StoredSettings.APP_FONT_SIZE`'s stored size (11pt if unset).
	:data:`StoredSettings.APP_FONT` (family, set via the **Preferences**
	dialog) overrides the family if a value has been stored, but the
	returned font's point size always comes from ``APP_FONT_SIZE``
	regardless, since a font saved via :meth:`preferences.Preferences.save_settings_btn`
	before ``APP_FONT_SIZE`` was introduced may otherwise carry its own,
	no-longer-relevant size. Shared by every top-level window
	(:class:`main.MainWindow`, :class:`can_viewer.CANViewer`,
	:class:`elf_viewer.ELFViewer`, :class:`remote_configs.RemoteConfigs`,
	:class:`preferences.Preferences`) so they all apply the same font via
	``self.setFont(...)``; windows with a menu bar additionally set the menu
	bar's font and a matching stylesheet, since ``QMenuBar``/``QMenu`` don't
	reliably pick up a parent widget's font otherwise.

	Returns:
		QFont | None: The font to apply, or ``None`` if the bundled font
			resource failed to load.
	"""
	logger = logging.getLogger(__name__)

	font_id = QFontDatabase.addApplicationFont(":/FiraCodeNerdFont-Regular.ttf")
	
	if font_id != -1:
		# 4. Extract the exact internal font family name
		font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
	
		# 5. Create a font object and apply it globally to the app
		app_font_size: int = int(StoredSettings.APP_FONT_SIZE.get(11))
		default_font = QFont(font_family, app_font_size)  # Family name and default size
		global_font: QFont = StoredSettings.APP_FONT.get(default_font)
		global_font.setPointSize(app_font_size)
		logger.info("Done Initializing Fonts")
		return global_font
	else:
		logger.error("Error: Could not load font from resources.")
		return None