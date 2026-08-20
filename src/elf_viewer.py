import logging
import os

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QFileDialog, QMainWindow, QTreeWidgetItem

from tools.elf_parser import ELFParser
from ui_elf_viewer import Ui_ElfViewer
from utils.ui_utils import get_global_font
from utils.wiz_utils.stored_settings import StoredSettings


class ELFViewer(QMainWindow, Ui_ElfViewer):
	def __init__(self, parent = None) -> None:
		super().__init__(parent)

		self.logger = logging.getLogger(__name__)
		
		self.setupUi(self)
		# Set icon
		self.setWindowIcon(QIcon(":/logo.png"))
		
		font = get_global_font()
		if font is not None:
			self.setFont(font)
			self.menuBar().setFont(font)
			self.menuBar().setStyleSheet(f"QMenuBar, QMenu {{ font: {font.pointSize()}pt '{font.family()}'; }}")

		self.parser = ELFParser()
		self.elf_file = StoredSettings.ELF_FILE.get("")
		self.elfFileLineEdit.setText(self.elf_file)

		# Connect event functions
		self.action_Open.triggered.connect(self.open_elf_file_btn)
		self.parseElfBtn.clicked.connect(self.parse_elf_file_btn)
		self.elfFileLineEdit.textEdited.connect(self.elf_file_text_changed)
		self.openFileBtn.clicked.connect(self.open_elf_file_btn)

		if self.elf_file != "":
			self.parse_elf_file_btn()

		self.sectionsWidget.setUpdatesEnabled(False)
		for i in range(self.sectionsWidget.columnCount()):
			self.sectionsWidget.resizeColumnToContents(i)
		self.sectionsWidget.setUpdatesEnabled(True)

	def open_elf_file_btn(self):
		elf_file, _ = QFileDialog.getOpenFileName(
			self,
			"Open File",
			StoredSettings.ELF_FILE.get(StoredSettings.get_documents_path()),
			"ELF Files (*.elf)"
		)

		if elf_file:
			StoredSettings.ELF_FILE.set(elf_file)
			self.elf_file = elf_file
			self.elfFileLineEdit.setText(elf_file)

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

		self.sectionsWidget.setUpdatesEnabled(False)
		for i in range(self.sectionsWidget.columnCount()):
			self.sectionsWidget.resizeColumnToContents(i)
		self.sectionsWidget.setUpdatesEnabled(True)

		self.archLineEdit.setText(out[1])
		self.startAddressLineEdit.setText(f"0x{out[2]:08X}")

	def elf_file_text_changed(self):
		text = self.elfFileLineEdit.text()
		
		if os.path.isfile(text):
			StoredSettings.ELF_FILE.set(text)
			self.elf_file = text