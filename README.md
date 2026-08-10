# dev-board-flasher

A PySide6 desktop application for flashing firmware onto development boards over a serial connection. Boards and flashing tools are both declared in TOML configuration files under `config/`, so new boards and flashing tools can be added without changing any code.

## Getting Started

1. Install dependencies (Python >= 3.10): `pip install -e .`
2. Compile the Qt UI and resource files: `make all`
3. Launch the app: `make run` (or `python src/main.py` after `make all`)

## Boards

Boards are declared as TOML files in `config/boards/`. See `config/example_board.toml` for a template:

| Key | Description |
| --- | --- |
| `board_name` | Human-readable name shown in the board dropdown. |
| `board_settings.flasher` | Name of the flashing tool used to program this board. Must match a `tool_name` in `config/flashing_tools/`. |
| `board_settings.baud_rate` | Baud rate used for flashing and the serial monitor. |
| `board_settings.type` | Board type. See `BoardType` in `src/utils/board_utils/board_type.py` for available options. |
| `board_settings.part_id` | Microcontroller part ID. See `BoardPartID` in `src/utils/board_utils/board_part_id.py` for available options. |

Boards are discovered and parsed automatically on startup by `BoardConfigurer`.

## Custom Flashing Tools

Flashing tools are declared as TOML files in `config/flashing_tools/`. See `config/example_flashing_tool.toml` for a template:

| Key | Description |
| --- | --- |
| `tool_name` | Name referenced by a board's `board_settings.flasher` value. |
| `tool_settings.type` | Either `cli` (runs an external command) or `python` (uses a built-in implementation, e.g. `esp32`). |
| `tool_settings.supported_boards` | List of board types this tool can flash. See `BoardType` for available options. |
| `tool_settings.supported_file_types` | Glob patterns of firmware files this tool accepts. |
| `tool_settings.args` | CLI-only. List of command-line arguments passed to the tool, in order. |

### How to use variables

`cli`-type tools can reference values from the board being flashed inside their `args` list by prepending a `$` to a variable name, similar to PowerShell string expansion (e.g. `"-p", "$partid"`). Variables are substituted at flash time before the command is run. See `config/flashing_tools/avrdude.toml` for an example.

#### Available Variables

| Variable | Description |
| --- | --- |
| `$partid` | The board's `PartID` name (from `board_settings.part_id`). |
| `$port` | The serial port selected in the app. |
| `$baudrate` | The board's configured baud rate. |
| `$boardname` | The board's `board_name`. |
| `$boardtype` | The board's `Type` name (from `board_settings.type`). |
| `$file` | Path to the firmware file selected for upload. |
