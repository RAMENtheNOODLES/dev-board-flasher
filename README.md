# dev-board-flasher

![GitHub License](https://img.shields.io/github/license/RAMENtheNOODLES/dev-board-flasher)
![GitHub Release](https://img.shields.io/github/v/release/RAMENtheNOODLES/dev-board-flasher)

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

Installed builds check the GitHub releases API for a newer version on startup, and on demand via **Help > Check for Updates**; self-update is only supported for compiled/installed builds, not when running from source. If a newer version is found and the user accepts the prompt, the app downloads that release's `dev-board-flasher-{version}-setup.exe` asset and silently re-runs it (`/SILENT /FORCECLOSEAPPLICATIONS`) — the same installer described above, so no separate "update" artifact is needed. The app then quits itself; a small detached helper (spawned by `apply_update`) waits for the installer to finish and relaunches it, rather than relying on the installer's own restart mechanism, which can't reach the actual running app in a Nuitka onefile build. See `Updater`/`check_for_updates`/`apply_update` in `src/utils/wiz_utils/`.

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
| `tool_settings.custom_settings.sub_settings` | CLI-only, optional. A table of one or more named sub-settings presets, each a table of extra `$variable` values merged in alongside the ones listed in [Available Variables](#available-variables). See [Sub-Settings](#sub-settings) below. |
| `tool_settings.use_pty` | CLI-only, optional. Runs the tool attached to a pseudo console (ConPTY) instead of a plain pipe. See [Pseudo Console (ConPTY)](#pseudo-console-conpty) below. Defaults to `false`. |
| `tool_settings.stop_on` | CLI-only, optional. A list of markers that, if seen in the tool's output, cause the process to be killed. See [Auto-Stopping the Process](#auto-stopping-the-process) below. Defaults to an empty list (never force-killed). |
| `tool_settings.progress_bar` | Optional. Settings controlling how the upload progress bar advances while this tool runs. See [Progress Bar](#progress-bar) below. |

Each key under `tool_settings.custom_settings` (e.g. `default`, `dry_run`) defines a separate argument list for that tool. All of a board's flasher's preset names are shown in the app's settings dropdown next to the upload button; the one selected there is passed as the `settings` argument to `flash()` and determines which argument list is used. A `default` preset is used if none is explicitly selected. See `config/flashing_tools/avrdude.toml`, which defines both a `default` preset and a `dry_run` preset that adds AVRDude's `-n` (no-write) flag.

Flashing tool TOML files can start with a `#:schema /config/flashing_tool_schema.json` directive (see the bundled `config/flashing_tools/*.toml`) to get editor validation and autocomplete against `config/flashing_tool_schema.json`.

### Progress Bar

`tool_settings.progress_bar` is an optional table that drives the upload progress bar shown next to the log box while a tool runs. If omitted, `method` defaults to `"none"` and the progress bar doesn't move.

| Key | Description |
| --- | --- |
| `method` | How progress is derived from the tool's output: `"none"`, `"step_array"`, or `"regex"`. |
| `num_steps` | Number of steps the bar is divided into. Used by `"step_array"`, where the bar's maximum is set to `num_steps - 1` and each matched step advances the bar's value by `1`, clamped at that maximum. |
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

A tool can define further variables of its own beyond this fixed list via `sub_settings` (see below).

### Sub-Settings

Some tools need arguments that vary by target in ways the fixed variable list above can't express (e.g. per-board memory offsets). `tool_settings.custom_settings.sub_settings` is a further table of named presets, each mapping extra variable names to values; the preset selected in the app's sub-settings dropdown (next to the main settings dropdown) is passed as the `sub_settings` argument to `flash()`, and its values are merged into the substitution variables available to the `custom_settings` argument list, so they can be referenced the same way (`"$offset"`, etc.). A `default` preset is used if none is explicitly selected; the dropdown itself is hidden whenever a tool defines one preset or fewer, same as the main settings dropdown.

```toml
[tool_settings.custom_settings]
default = [
    "-flash", "$file",
    "-offset", "$offset", "-size", "$size",
]

[tool_settings.custom_settings.sub_settings]
default  = { offset = "0x0000", size = "0x8000" }
profile2 = { offset = "0x8000", size = "0x8000" }
```

### Pseudo Console (ConPTY)

Some CLI tools write progress/status via Win32 console APIs (`WriteConsole`, colored `SetConsoleTextAttribute` output) rather than plain stdout writes. Those calls silently no-op when stdout/stderr are plain anonymous pipes -- which is what the tool gets by default -- so such tools produce no captured output at all, even though the same binary logs fine when run in a real terminal window. Setting `tool_settings.use_pty = true` runs the tool attached to a pseudo console (ConPTY) instead, giving it a real console handle so those calls behave as they do interactively. Leave `false`/omitted for tools that just print normally (e.g. AVRDude) -- it's extra overhead a well-behaved tool doesn't need. See `ConPtyProcess` in `src/utils/flashing_tools/conpty_process.py`.

### Auto-Stopping the Process

Some CLI tools finish their real work but then hang on a blocking prompt (e.g. "press enter to exit") instead of exiting on their own, which would otherwise hang the flash indefinitely. `tool_settings.stop_on` is a list of markers; as soon as one is seen in the tool's output, the process is killed. Matching is a plain substring check against each chunk of output, not a regex, so pick a marker that's an exact fragment of the tool's real output:

```toml
stop_on = ["Press any key to continue"]
```

Because this force-kills the process rather than letting it exit on its own, the exit code the app reports afterward is a synthetic non-zero value, not whatever code the tool itself would have chosen -- Windows has no way to read back a process's "real" exit code before it actually calls `ExitProcess`.

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

These are stored via `QSettings` (see `src/utils/wiz_utils/stored_settings.py`) in an INI file under the OS's standard per-user config directory (e.g. `%LOCALAPPDATA%\flashwiz\flash_wiz_settings.ini` on Windows). Each setting's key is namespaced under a section (e.g. `board_flashing/selected_board`); older builds stored the same value under its bare key instead (e.g. `selected_board`), so `StoredSettings.transfer_legacy_settings()` runs as the first startup task on every launch to copy any value still sitting under its old flat key over to its new sectioned one, after first backing up the whole INI file (see `StoredSettings.backup_settings()`). **Edit > Preferences > Clear All Settings** wipes all of the above (after a confirmation prompt).

## Preferences

**Edit > Preferences...** opens a settings dialog with two tabs:

- **General** lets you override the app's font (family and size) via a font picker and size spinner; **Save Settings** stores the choice in `StoredSettings.APP_FONT`/`StoredSettings.APP_FONT_SIZE` and applies it the next time the app starts or is reloaded (**Edit > Reload App**), not immediately, while **Revert to Defaults** clears the override back to the bundled Nerd Font at 11pt. The chosen font applies to every top-level window, including the CAN Viewer and ELF Parser (see `get_global_font` in `src/utils/ui_utils/`, and [Styling](#styling) below for how it's actually applied app-wide).
- **Advanced** holds **Import Settings**/**Export Settings** (read/write the whole settings file as an INI you pick, backing up the current file first on import; see `StoredSettings.import_settings`/`export_settings`) and **Clear All Settings** (moved here from the old Tools menu). A successful import asks whether to reload the app immediately (**Edit > Reload App**'s `reload_app()`, see `src/utils/wiz_utils/`) to pick up the imported settings right away; declining just refreshes the dialog's own font/size preview instead.

## Styling

The app's whole look (colors, borders, hover/pressed/disabled states, etc.) comes from a single stylesheet, `assets/style.qss`, applied once via `QApplication.setStyleSheet()` in `src/main.py`. Its palette is sampled directly from `assets/logo.png` (black, indigo, cyan, yellow, white); every other color in the file is a tint or shade mixed from those five, so the UI and the app icon stay visually consistent.

Like the bundled font, `style.qss` is compiled into the app as a Qt resource rather than read from disk at runtime: it's listed in `assets/images.qrc` alongside `logo.png`, compiled to `src/images_rc.py` by `make rcc` (part of `make all`), and loaded at startup via `get_global_stylesheet()` in `src/utils/ui_utils/` (mirroring `get_global_font()`'s pattern), which reads the embedded `:/style.qss` resource. Editing `assets/style.qss` requires re-running `make rcc`/`make all` (or `make run`, which does this automatically) for the change to show up.

Applying a stylesheet at the `QApplication` level has one non-obvious consequence: once any stylesheet is set app-wide, Qt resolves the font of every styled widget from `QApplication.font()` rather than from the font its parent window was given via `self.setFont(...)`. Because of this, `src/main.py` also calls `app.setFont(...)` with the same font `get_global_font()` returns, once per pass through the app's restart loop (so a font changed in Preferences takes effect on the reload it triggers, same as the font applied to each window itself). Without this, only widgets given their own explicit font in QSS (like the menu bar, which sets `font:` directly in its own stylesheet — see `get_global_font`'s docstring) would pick up the chosen font; everything else would silently fall back to the OS default.

## Board and Config Cache

Parsed board and flashing-tool config files (including remote ones fetched over the network) are cached to disk between launches under the OS's standard per-user cache directory (e.g. `%LOCALAPPDATA%\flashwiz\cache` on Windows), so `config/boards`, `config/flashing_tools`, and any GitHub-hosted remote configs aren't fully re-read/re-fetched on every startup. Each cache file is hashed on write and the hash checked on read (see `CacheHelper` in `src/utils/wiz_utils/cache_helper.py`), so a cache file changed outside the app is treated as untrusted and rebuilt rather than loaded.

If a config change (local or remote) isn't showing up after a restart, use **Edit > Invalidate Cache** to clear the board cache and the GitHub response cache and restart the app, forcing everything to be re-read from source.

## Tools

**Tools > CAN** opens a standalone CAN viewer for connecting to a Kvaser CAN device, decoding traffic against a loaded DBC file, and browsing its messages/signals. It requires the [Kvaser CANlib SDK/drivers](https://kvaser.com/canlib-sdk/) to be installed separately; the app will warn and refuse to open the tool if they're missing. Connecting and receiving frames both run on a background thread so the UI doesn't freeze while waiting on the CAN driver.

**Tools > ELF Parser** opens a standalone viewer for inspecting a compiled `.elf` firmware image: pick a file and click **Parse Elf File** to list its sections (name, start address, size, and type) alongside the file's target architecture. The start address field is set from the `.vectors` section, if the ELF has one. Parsing is handled by `ELFParser.parse_elf()` (`src/tools/elf_parser.py`), built on [pyelftools](https://github.com/eliben/pyelftools).

## AI Use

This project uses AI for documentation and certain functions
