"""Factories for writing real-shaped board/flashing-tool TOML config files to disk.

These are hand-written from the schema actually used by config/boards/*.toml
and config/flashing_tools/*.toml, rather than copies of those real files, so
a test's fixture data can't silently drift when someone edits config/ for an
unrelated reason.
"""

from pathlib import Path


def write_board_toml(
	directory: Path,
	filename: str = "board.toml",
	board_name: str = "Test Board",
	flasher: str = "avrdude",
	baud_rate: int = 115200,
	board_type: str = "arduino",
	part_id: str = "atmega328p",
	supported_files: list[str] | None = None,
) -> Path:
	if supported_files is None:
		supported_files = ["*.hex", "*.bin"]

	supported_files_toml = ", ".join(f'"{f}"' for f in supported_files)

	content = (
		f'board_name = "{board_name}"\n'
		"\n"
		"[board_settings]\n"
		f'flasher = "{flasher}"\n'
		f"baud_rate = {baud_rate}\n"
		f'type = "{board_type}"\n'
		f'part_id = "{part_id}"\n'
		"\n"
		f"supported_files = [{supported_files_toml}]\n"
	)

	path = directory / filename
	path.write_text(content, encoding="utf-8")
	return path


def write_tool_toml(
	directory: Path,
	filename: str = "tool.toml",
	tool_name: str = "testtool",
	tool_loc: str = "",
	tool_type: str = "cli",
	supported_boards: list[str] | None = None,
	supported_file_types: list[str] | None = None,
	custom_settings: dict[str, list[str]] | None = None,
	progress_bar_method: str = "step_array",
	progress_bar_num_steps: int = 100,
	inc_step_on: list[str] | None = None,
	regex_method: str | None = None,
	step_read_regex: str | None = None,
	step_final_regex: str | None = None,
	initial_address: str | None = None,
	final_address: str | None = None,
	next_address: str | None = None,
	use_pty: bool | None = None,
	stop_on: list[str] | None = None,
) -> Path:
	if supported_boards is None:
		supported_boards = ["ARDUINO"]
	if supported_file_types is None:
		supported_file_types = ["*.hex", "*.bin"]
	if inc_step_on is None:
		inc_step_on = ["#"]

	supported_boards_toml = ", ".join(f'"{b}"' for b in supported_boards)
	supported_file_types_toml = ", ".join(f'"{f}"' for f in supported_file_types)
	inc_step_on_toml = ", ".join(f'"{marker}"' for marker in inc_step_on)

	custom_settings_toml = ""
	if custom_settings:
		custom_settings_toml = "\n[tool_settings.custom_settings]\n"
		for name, args in custom_settings.items():
			args_toml = ", ".join(f'"{a}"' for a in args)
			custom_settings_toml += f"{name} = [{args_toml}]\n"

	# TOML literal strings ('...') so regex patterns with backslashes don't
	# need escaping.
	progress_bar_extra = ""
	for key, value in (
		("regex_method", regex_method),
		("step_read_regex", step_read_regex),
		("step_final_regex", step_final_regex),
		("initial_address", initial_address),
		("final_address", final_address),
		("next_address", next_address),
	):
		if value is not None:
			progress_bar_extra += f"{key} = '{value}'\n"

	use_pty_toml = ""
	if use_pty is not None:
		use_pty_toml = f"use_pty = {str(use_pty).lower()}\n"

	stop_on_toml = ""
	if stop_on is not None:
		stop_on_toml = "stop_on = [{}]\n".format(", ".join(f'"{marker}"' for marker in stop_on))

	content = (
		f'tool_name = "{tool_name}"\n'
		f'tool_loc = "{tool_loc}"\n'
		"\n"
		"[tool_settings]\n"
		f'type = "{tool_type}"\n'
		f"supported_boards = [{supported_boards_toml}]\n"
		f"supported_file_types = [{supported_file_types_toml}]\n"
		f"{use_pty_toml}"
		f"{stop_on_toml}"
		f"{custom_settings_toml}"
		"\n"
		"[tool_settings.progress_bar]\n"
		f'method = "{progress_bar_method}"\n'
		f"num_steps = {progress_bar_num_steps}\n"
		f"inc_step_on = [{inc_step_on_toml}]\n"
		f"{progress_bar_extra}"
	)

	path = directory / filename
	path.write_text(content, encoding="utf-8")
	return path
