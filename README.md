# dev-board-flasher

A PySide6 desktop application for flashing firmware onto development boards over a serial connection. Boards and flashing tools are both declared in TOML configuration files under `config/`, so new boards and flashing tools can be added without changing any code.

## Installing the Tool

### From source

1. Clone the repository and `cd` into it.
2. Install the project and its dependencies in editable mode (Python >= 3.10 required): `pip install -e .`
3. Compile the Qt UI (`ui/main_window.ui`) and resource files into `src/ui_main_window.py`, `src/fonts_rc.py`, etc.: `make all`
4. Run the app with `make run`, or directly with `python src/main.py`.

### As a standalone build

The app can also be packaged into a standalone executable with [Nuitka](https://nuitka.net/) using the included `src/pysidedeploy.spec`, via `pyside6-deploy`. The resulting build bundles its own `config/` directory with the boards and flashing tools shipped in this repo; use the external directory settings below to add your own without rebuilding.

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
| `tool_loc` | Physical location of the flashing tool, leave blank to use the system PATH. |
| `tool_settings.type` | Either `cli` (runs an external command) or `python` (uses a built-in implementation, e.g. `esp32`). |
| `tool_settings.supported_boards` | List of board types this tool can flash. See `BoardType` for available options. |
| `tool_settings.supported_file_types` | Glob patterns of firmware files this tool accepts. |
| `tool_settings.custom_settings` | CLI-only. A table of one or more named settings presets, each a list of command-line arguments passed to the tool, in order. |

Each key under `tool_settings.custom_settings` (e.g. `default`, `dry_run`) defines a separate argument list for that tool. All of a board's flasher's preset names are shown in the app's settings dropdown next to the upload button; the one selected there is passed as the `settings` argument to `flash()` and determines which argument list is used. A `default` preset is used if none is explicitly selected. See `config/flashing_tools/avrdude.toml`, which defines both a `default` preset and a `dry_run` preset that adds AVRDude's `-n` (no-write) flag.

### How to use variables

`cli`-type tools can reference values from the board being flashed inside a `custom_settings` preset's argument list by prepending a `$` to a variable name, similar to PowerShell string expansion (e.g. `"-p", "$partid"`). Variables are substituted at flash time before the command is run. See `config/flashing_tools/avrdude.toml` for an example.

#### Available Variables

| Variable | Description |
| --- | --- |
| `$partid` | The board's `PartID` name (from `board_settings.part_id`). |
| `$port` | The serial port selected in the app. |
| `$baudrate` | The board's configured baud rate. |
| `$boardname` | The board's `board_name`. |
| `$boardtype` | The board's `Type` name (from `board_settings.type`). |
| `$file` | Path to the firmware file selected for upload. |

## External Board and Flashing Tool Directories

Boards and flashing tools don't have to live inside the app's built-in `config/` directory. You can point the app at additional external folders (e.g. for boards/tools you maintain separately, or when running a packaged build) from the **Edit** menu:

- **Edit > Add External Board Directory** opens a folder picker for an external folder of board TOML files.
- **Edit > Add External Flashing Tool Directory** opens a folder picker for an external folder of flashing tool TOML files.

Each TOML file in the selected folder is loaded in addition to (not instead of) the boards/tools bundled in `config/boards` and `config/flashing_tools`. After picking a folder, the app restarts automatically to pick up the new configuration files.

The selected paths are remembered between launches (stored via `QSettings` under the `CookieJAR`/`wizlog` organization/application name). To stop using an external folder, pick a different one, or clear the corresponding value from your OS's settings storage (e.g. the Windows Registry under `HKEY_CURRENT_USER\Software\CookieJAR\wizlog`).
