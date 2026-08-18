import logging

from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QFont, QFontDatabase, QIcon
from PySide6.QtWidgets import QFileDialog, QMainWindow, QTreeWidgetItem

from tools.elf_parser import ELFParser
from ui_elf_viewer import Ui_ElfViewer
from utils.wiz_utils.stored_settings import StoredSettings


class ELFViewer(QMainWindow, Ui_ElfViewer):
	def __init__(self, parent = None) -> None:
		super().__init__(parent)

		self.logger = logging.getLogger(__name__)
		
		self.setupUi(self)
		# Set icon
		self.setWindowIcon(QIcon(":/logo.png"))
		font_id = QFontDatabase.addApplicationFont(":/FiraCodeNerdFont-Regular.ttf")
		
		if font_id != -1:
			# 4. Extract the exact internal font family name
			font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
		
			# 5. Create a font object and apply it globally to the app
			global_font = QFont(font_family, 12)  # Family name and default size
			self.setFont(global_font)
			self.logger.info("Done Initializing Fonts")
		else:
			self.logger.error("Error: Could not load font from resources.")
		
		QCoreApplication.setOrganizationDomain("CookieJAR")
		QCoreApplication.setApplicationName("flashwiz")

		self.parser = ELFParser()
		self.elf_file = StoredSettings.ELF_FILE.get("")

		# Connect event functions
		self.action_Open.triggered.connect(self.open_elf_file_btn)
		self.parseElfBtn.clicked.connect(self.parse_elf_file_btn)

		for i in range(self.sectionsWidget.columnCount()):
			self.sectionsWidget.resizeColumnToContents(i)

	def open_elf_file_btn(self):
		self.elf_file, _ = QFileDialog.getOpenFileName(
			self,
			"Open File",
			self.elf_file,
			"ELF Files (*.elf)"
		)

		if self.elf_file:
			StoredSettings.ELF_FILE.set(self.elf_file)

	def parse_elf_file_btn(self):
		if self.elf_file == "":
			return

		out = self.parser.parse_elf(self.elf_file)
		self.logger.debug(f"Parser output: {out}")

		if out is None:
			return

		self.sectionsWidget.clear()

		for section, data in zip(out[3].keys(), out[3].values()):
			new_item = QTreeWidgetItem(self.sectionsWidget)
			new_item.setText(0, section) # Section Name
			new_item.setText(1, f"0x{data[0]:08X}") # Section Address
			new_item.setText(2, f"0x{data[1]:08X}") # Section Size
			new_item.setText(3, data[2]) # Section Type

		for i in range(self.sectionsWidget.columnCount()):
			self.sectionsWidget.resizeColumnToContents(i)

		self.archLineEdit.setText(out[1])
		self.startAddressLineEdit.setText(f"0x{out[2]:08X}")