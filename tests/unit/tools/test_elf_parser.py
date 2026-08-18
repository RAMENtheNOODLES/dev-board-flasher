from pathlib import Path

import tools.elf_parser as elf_parser_module
from tools.elf_parser import ELFParser


class _FakeSection:
	def __init__(self, name: str, sh_addr: int, sh_size: int, sh_type: str):
		self.name = name
		self.header = {"sh_addr": sh_addr, "sh_size": sh_size}
		self._sh_type = sh_type

	def __getitem__(self, key):
		if key == "sh_type":
			return self._sh_type
		raise KeyError(key)


class _FakeELFFile:
	def __init__(self, stream, sections, machine="ARM", entry=0x1000, e_type="ET_EXEC"):
		self.stream = stream
		self.header = {"e_machine": machine, "e_entry": entry, "e_type": e_type}
		self._sections = sections

	def iter_sections(self):
		return iter(self._sections)

	def get_machine_arch(self):
		return self.header["e_machine"]


def _patch_elffile(monkeypatch, sections, **kwargs):
	monkeypatch.setattr(
		elf_parser_module,
		"ELFFile",
		lambda stream: _FakeELFFile(stream, sections, **kwargs),
	)


def _dummy_elf_path(tmp_path: Path) -> str:
	# ELFFile itself is faked out, so the real file's contents never matter -
	# parse_elf just needs a path it can open() in "rb" mode.
	path = tmp_path / "firmware.elf"
	path.write_bytes(b"")
	return str(path)


def test_parse_elf_returns_filename_arch_start_address_and_sections(monkeypatch, tmp_path):
	sections = [
		_FakeSection(".vectors", 0x0800_0000, 0x200, "SHT_PROGBITS"),
		_FakeSection(".text", 0x0800_0200, 0x1000, "SHT_PROGBITS"),
	]
	_patch_elffile(monkeypatch, sections, machine="ARM")
	filename = _dummy_elf_path(tmp_path)

	result = ELFParser.parse_elf(filename)

	assert result == (
		filename,
		"ARM",
		0x0800_0000,
		{
			".vectors": (0x0800_0000, 0x200, "SHT_PROGBITS"),
			".text": (0x0800_0200, 0x1000, "SHT_PROGBITS"),
		},
	)


def test_parse_elf_defaults_start_address_to_zero_without_a_vectors_section(monkeypatch, tmp_path):
	sections = [_FakeSection(".text", 0x0800_0200, 0x1000, "SHT_PROGBITS")]
	_patch_elffile(monkeypatch, sections)
	filename = _dummy_elf_path(tmp_path)

	_, _, start_addr, _ = ELFParser.parse_elf(filename)

	assert start_addr == 0


def test_parse_elf_returns_an_empty_sections_dict_for_a_file_with_no_sections(monkeypatch, tmp_path):
	_patch_elffile(monkeypatch, sections=[])
	filename = _dummy_elf_path(tmp_path)

	_, _, _, sections = ELFParser.parse_elf(filename)

	assert sections == {}


def test_parse_elf_reports_the_files_machine_architecture(monkeypatch, tmp_path):
	_patch_elffile(monkeypatch, sections=[], machine="Xtensa")
	filename = _dummy_elf_path(tmp_path)

	_, arch, _, _ = ELFParser.parse_elf(filename)

	assert arch == "Xtensa"


def test_parse_elf_can_be_called_without_constructing_an_elfparser_instance(monkeypatch, tmp_path):
	"""parse_elf is a @staticmethod, so callers (e.g. ELFViewer) can - and do -
	call it via an instance (self.parser.parse_elf(...)) even though it takes
	no self/cls. Guard against that method accidentally requiring the
	instance/class as its first positional argument.
	"""
	_patch_elffile(monkeypatch, sections=[])
	filename = _dummy_elf_path(tmp_path)

	parser = ELFParser()
	result = parser.parse_elf(filename)

	assert result[0] == filename
