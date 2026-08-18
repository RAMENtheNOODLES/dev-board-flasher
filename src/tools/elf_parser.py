from typing import Any
from elftools.elf.elffile import ELFFile

import logging



class ELFParser:
	def __init__(self) -> None:
		self.logger = logging.getLogger(__name__)

	@staticmethod
	def parse_elf(filename: str):
		with open(filename, "rb") as f:
			elffile = ELFFile(f)

			header = elffile.header

			print(f"--- ELF Header ---")
			print(f"Architecture: {header['e_machine']}")
			print(f"Entry Point:  {hex(header['e_entry'])}")
			print(f"Type:         {header['e_type']}\n")
			
			# 2. Iterate through sections
			print(f"--- Sections ---")
			for section in elffile.iter_sections():
				print(f"Name: {section.name:<20} | Type: {section['sh_type']}")