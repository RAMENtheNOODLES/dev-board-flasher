import logging

from elftools.elf.elffile import ELFFile

SectionOutput = tuple[
	int, # Start address
	int, # Size
	str, # section type
]

Sections = dict[
	str, # Section name
	SectionOutput
]

ELFOutput = tuple[
	str, # File name
	str, # arch
	int, # Start Address

	Sections, # List of sections in elf file
]

class ELFParser:
	def __init__(self) -> None:
		self.logger = logging.getLogger(__name__)

	@staticmethod
	def parse_elf(filename: str) -> ELFOutput|None:
		logger = logging.getLogger(__name__)
		with open(filename, "rb") as f:
			elffile = ELFFile(f)

			start_addr: int = elffile.header["e_entry"]

			header = elffile.header

			logger.debug("--- ELF Header ---")
			logger.debug(f"Architecture: {header['e_machine']}")
			logger.debug(f"Entry Point:  {hex(header['e_entry'])}")
			logger.debug(f"Type:         {header['e_type']}\n")
			
			# 2. Iterate through sections
			logger.debug("--- Sections ---")

			sections: Sections = {}

			for section in elffile.iter_sections():
				section_name = section.name
				section_start_addr = section.header["sh_addr"]
				section_size = section.header["sh_size"]
				section_type = section["sh_type"]
				logger.debug(f"Name: {section_name:<20} | Start Address: 0x{section_start_addr:08X} | Size: 0x{section_size:04X}")
				section_info: SectionOutput = (section_start_addr, section_size, section_type)

				if section_name == ".vectors":
					start_addr = section_start_addr

				sections[section.name] = section_info

			return (filename, elffile.get_machine_arch(), start_addr, sections)

		return None

			