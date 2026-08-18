# dev-board-flasher

A PySide6 desktop application for flashing firmware onto development boards over a serial connection. Boards and flashing tools are both declared in TOML configuration files under `config/`, so new boards and flashing tools can be added without changing any code.

## Installing the Tool

### From source

1. Clone the repository and `cd` into it.
2. Install the project and its dependencies in editable mode (Python >= 3.10 required): `pip install -e .`
3. Compile the Qt UI (`ui/main_window.ui`) and resource files into `src/ui_main_window.py`, `src/fonts_rc.py`, etc.: `make all`
4. Run the app with `make run`, or directly with `python src/main.py`.

### As a standalone build

The app can also be packaged into a standalone executable with [Nuitka](https://nuitka.net/) using the included `src/pysidedeploy.spec`, via `pyside6-deploy` (`make compile`). The resulting build bundles its own `config/` directory with the boards and flashing tools shipped in this repo; use the external directory settings below to add your own without rebuilding.

### As a Windows installer

`make installer` (requires [Inno Setup](https://jrsoftware.org/isinfo.php)'s `ISCC.exe` on `PATH`) wraps the standalone build above in a Windows installer, built from `scripts/installer.iss`. It installs to `%LOCALAPPDATA%\Programs\flashwiz` without requiring admin rights (falling back to the machine-wide `Program Files` if run elevated instead), and adds Start Menu/Desktop shortcuts. The installer's version is always read from `pyproject.toml` at build time, so it can't drift out of sync with the app it's packaging.

Every push builds both the portable zip and this installer via [`.github/workflows/release.yml`](.github/workflows/release.yml): pushes to `main` attach both as assets on a GitHub Release, while every other branch gets them as a downloadable Actions artifact instead. Pushes to a branch with an open pull request skip this build entirely (including rebases/force-pushes of that branch) — only the test suite below runs for those, via `tests.yml`'s own `pull_request` trigger.

## Updating

Installed builds check the GitHub releases API for a newer version on startup, and on demand via **Help > Check for Updates**; self-update is only supported for compiled/installed builds, not when running from source. If a newer version is found and the user accepts the prompt, the app downloads that release's `dev-board-flasher-{version}-setup.exe` asset and silently re-runs it (`/SILENT /FORCECLOSEAPPLICATIONS /RESTARTAPPLICATIONS`), which closes the running app, reinstalls over the existing install directory, and relaunches it automatically — the same installer described above, so no separate "update" artifact is needed. See `Updater`/`check_for_updates`/`apply_update` in `src/utils/wiz_utils/`.

Passing `--force-update` on the command line skips the version check and always offers the latest release, regardless of whether it's newer than the installed version — useful for testing the update flow itself without waiting for a new release.

## Running Tests

Install the dev dependencies (`pip install -e ".[dev]"`), then run the suite with `make test`, or directly with `pytest` from the repo root. Tests live under `tests/`, split into `tests/unit` (pure logic, no Qt event loop or real hardware) and `tests/integration` (needs `pytest-qt`/heavier fixtures, e.g. a running `QApplication`); integration tests are marked `@pytest.mark.integration` and can be skipped with `pytest -m "not integration"` for a faster local loop. `tests/fixtures` holds hand-written TOML factories used across both.

Every push and pull request also runs the suite on Windows via [`.github/workflows/tests.yml`](.github/workflows/tests.yml) (headless, with `QT_QPA_PLATFORM=offscreen`), followed by a report-only `ruff check` pass that doesn't yet gate the build.

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
| `tool_settings.progress_bar` | Optional. Settings controlling how the upload progress bar advances while this tool runs. See [Progress Bar](#progress-bar) below. |

Each key under `tool_settings.custom_settings` (e.g. `default`, `dry_run`) defines a separate argument list for that tool. All of a board's flasher's preset names are shown in the app's settings dropdown next to the upload button; the one selected there is passed as the `settings` argument to `flash()` and determines which argument list is used. A `default` preset is used if none is explicitly selected. See `config/flashing_tools/avrdude.toml`, which defines both a `default` preset and a `dry_run` preset that adds AVRDude's `-n` (no-write) flag.

Flashing tool TOML files can start with a `#:schema /config/flashing_tool_schema.json` directive (see the bundled `config/flashing_tools/*.toml`) to get editor validation and autocomplete against `config/flashing_tool_schema.json`.

### Progress Bar

`tool_settings.progress_bar` is an optional table that drives the upload progress bar shown next to the log box while a tool runs. If omitted, `method` defaults to `"none"` and the progress bar doesn't move.

| Key | Description |
| --- | --- |
| `method` | How progress is derived from the tool's output: `"none"`, `"step_array"`, or `"regex"`. |
| `num_steps` | Number of steps the bar is divided into. Used by `"step_array"`, where each matched step advances the bar by `100 // num_steps`. |
| `inc_step_on` | `"step_array"` only. A list of markers to watch for in the tool's output, in order. Each time the current marker is found, the bar advances and moves on to the next marker, wrapping back to the first once the list is exhausted. |
| `regex_method` | `"regex"` only. Which regex strategy to use: `"normal"` (current/total counts) or `"hex"` (hex memory addresses). Defaults to `"normal"`. |
| `step_read_regex` | `"regex"` with `regex_method = "normal"` only. A regular expression matching the current step count in the tool's output (e.g. the `12` in `"12/50"`). |
| `step_final_regex` | `"regex"` with `regex_method = "normal"` only. A regular expression matching the total step count in the tool's output (e.g. the `50` in `"12/50"`). |
| `initial_address` | `"regex"` with `regex_method = "hex"` only. A regular expression matching the starting hex address of the flash range in the tool's output. |
| `final_address` | `"regex"` with `regex_method = "hex"` only. A regular expression matching the ending hex address of the flash range; combined with `initial_address` to set the bar's maximum (`final - initial`). |
| `next_address` | `"regex"` with `regex_method = "hex"` only. A regular expression matching the current hex address reached; combined with `initial_address` to set the bar's value (`next - initial`) as flashing progresses. |

`"step_array"` suits tools that print a repeating character per unit of work (e.g. AVRDude's `#` progress dots); `"regex"` suits tools that print an explicit `current/total` count (`regex_method = "normal"`, e.g. esptool's `12/50` write progress) or that report progress as absolute hex flash addresses (`regex_method = "hex"`). See `config/flashing_tools/avrdude.toml` and `config/flashing_tools/esp32.toml` for an example of each.

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

## Remote Board and Flashing Tool Configs

Boards and flashing tools don't have to live inside the app's built-in `config/` directory. From **Edit > Remote Configurations** you can add extra board/flashing-tool TOML files by local path or GitHub file URL (either a normal `github.com/{owner}/{repo}/blob/{ref}/{path}` link, as seen when browsing a repo, or a `raw.githubusercontent.com` link) — each entry is loaded in addition to (not instead of) the boards/tools bundled in `config/boards` and `config/flashing_tools`, and is automatically treated as a board or a flashing tool based on whether its TOML declares a `board_name` or `tool_name` key.

The **Remote Configurations** dialog lets you add rows by typing/pasting a path or URL directly, or via a file picker for local files, and edit or remove existing rows; the list is only saved when the dialog is accepted (e.g. clicking OK). Picking up added, edited, or removed entries requires restarting the app, either manually from **Edit > Reload App** or by relaunching.

The list is remembered between launches (see `StoredSettings.REMOTE_CONFIGS` in `src/utils/wiz_utils/stored_settings.py`, and [Remembered Session State](#remembered-session-state) below for where that's stored).

Each board/flashing-tool config file's parsed contents are also cached to disk (see [Board and Config Cache](#board-and-config-cache) below), so remote URLs aren't re-fetched on every startup; use **Edit > Invalidate Cache** after editing a remote file if the app doesn't pick up the change.

### Fetching from private GitHub repos

GitHub URLs are fetched through the GitHub Contents API (works for both public and private repos), which requires a personal access token (PAT) with read access to the repo. Set one from **Edit > Github Personal Access Token**; unlike the settings above, it's stored in your OS's credential store (via [`keyring`](https://pypi.org/project/keyring/)) rather than in the settings file, since it's a secret. See [docs/github_token.md](docs/github_token.md) for a walkthrough of creating a suitable token. Successful responses are also cached in memory for 10 minutes to avoid hammering the API on repeated refreshes; **Edit > Invalidate Cache** clears this too.

## Remembered Session State

Beyond the remote configs above, the app remembers the following between launches so it reopens the way you left it:

- The selected board.
- The selected flash tool settings preset.
- The selected baud rate.
- The last firmware file chosen (via the file picker or drag-and-drop).
- The last CAN DBC file loaded in the CAN viewer (see [Tools](#tools) below).
- The last ELF file loaded in the ELF parser (see [Tools](#tools) below).

These are stored via `QSettings` (see `src/utils/wiz_utils/stored_settings.py`) in an INI file under the OS's standard per-user config directory (e.g. `%LOCALAPPDATA%\flashwiz\flash_wiz_settings.ini` on Windows), rather than the Windows registry used by older builds; settings left over from that legacy location are migrated into the file automatically the first time you launch a build with this change. **Tools > Clear All Settings** wipes all of the above (after a confirmation prompt).

## Board and Config Cache

Parsed board and flashing-tool config files (including remote ones fetched over the network) are cached to disk between launches under the OS's standard per-user cache directory (e.g. `%LOCALAPPDATA%\flashwiz\cache` on Windows), so `config/boards`, `config/flashing_tools`, and any GitHub-hosted remote configs aren't fully re-read/re-fetched on every startup. Each cache file is hashed on write and the hash checked on read (see `CacheHelper` in `src/utils/wiz_utils/cache_helper.py`), so a cache file changed outside the app is treated as untrusted and rebuilt rather than loaded.

If a config change (local or remote) isn't showing up after a restart, use **Edit > Invalidate Cache** to clear the board cache and the GitHub response cache and restart the app, forcing everything to be re-read from source.

## Tools

**Tools > CAN** opens a standalone CAN viewer for connecting to a Kvaser CAN device, decoding traffic against a loaded DBC file, and browsing its messages/signals. It requires the [Kvaser CANlib SDK/drivers](https://kvaser.com/canlib-sdk/) to be installed separately; the app will warn and refuse to open the tool if they're missing. Connecting and receiving frames both run on a background thread so the UI doesn't freeze while waiting on the CAN driver.

**Tools > ELF Parser** opens a standalone viewer for inspecting a compiled `.elf` firmware image: pick a file and click **Parse Elf File** to list its sections (name, start address, size, and type) alongside the file's target architecture. The start address field is set from the `.vectors` section, if the ELF has one. Parsing is handled by `ELFParser.parse_elf()` (`src/tools/elf_parser.py`), built on [pyelftools](https://github.com/eliben/pyelftools).

## AI Use

This project uses AI for documentation and certain functions
