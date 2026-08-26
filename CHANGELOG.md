<!-- markdownlint-disable MD024 -->
# Changelog

All notable changes to dev-board-flasher are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [1.8.4] - 2026-08-26

### Added

### Changed

- Fixed issue with pya2l library

## [1.8.1] - 2026-08-25

### Added

- GitHub token dialog (**Edit > Github Personal Access Token...**): a
  **Clear Token** button that, after a confirmation prompt, clears the
  stored token and its associated cache and empties the token field.
- **A2L Parser** (**Tools > A2L Parser**): parses an A2L (ASAP2) calibration
  file and displays each module's Measurements, Characteristics, Compu
  Methods, Functions, Groups, Axis Points, Record Layouts, and Units in a
  tree.
  - Several real-world quirks are corrected ahead of parsing so files that
    fail pya2l's strict grammar still load: a leading UTF-8 BOM; reserved
    ASAP2 keywords (e.g. `RAM`) used as bare values inside vendor `IF_DATA`
    blocks, which pya2l's generic grammar rejects; an unquoted `FORMAT`
    spec; and a `MATRIX_DIM` given fewer than its hardcoded 3 dimensions.
- **Main Menu Status Bar**: a status bar that shows certain messages when
  performing specific tasks.
- **CAN Viewer**: a permanent bus-load meter in the status bar - a
  color-coded progress bar (green under 50%, yellow up to 80%, red above
  that) showing the current CAN bus load, refreshed roughly once a second
  while connected.
- **CAN Viewer**: parses J1939 DM1 (Active Diagnostic Trouble Codes)
  messages, including reassembly of multi-packet broadcasts via the SAE
  J1939-21 BAM transport protocol. Decoded lamp status and DTCs (SPN, FMI,
  occurrence count, SPN conversion method) get their own row per source
  address in the message tree.
  - **File > Configure J1939**: load SPN- and FMI-to-name lookup CSVs so
    DTC rows show human-readable names (e.g. "Engine Oil Pressure")
    alongside their raw codes.
- **CAN Viewer**: **Transmit Settings** window for periodically sending
  DBC messages onto the bus - pick a message (labeled by its J1939 PGN), a
  send rate, a value for each signal (a dropdown of the DBC's defined
  labels for a signal with a value table), and whether it's active. Takes
  effect immediately while connected, auto-resizes to fit its table, and
  is remembered across app restarts.
- **CAN Viewer**: the message tree now also shows messages this app
  transmits (e.g. via Transmit Settings), alongside received traffic, with
  a DIR column indicating RX vs TX.

### Changed

- **release.yml**: Fixed an issue where it used the workflow's trigger commit
  rather than the branch tip.
- **CAN Viewer**: a signal decoded from a DBC value table (enum) now shows
  its defined label (e.g. "On") instead of the raw physical number, in
  both the message tree and CSV logging.
- GitHub token dialog: submitting with an empty access token field now
  offers **Ignore** alongside **Ok** on the warning, letting you save an
  empty token instead of only dismissing the warning.
- CI: the `develop`-onto-`main` rebase (formerly the standalone
  `sync-develop.yml`, triggered independently on every push to `main`)
  is now a step in the release workflow itself, sequenced to run right
  after the version-bump/changelog-promotion commit is pushed and before
  `build` compiles the release. Previously the two workflows could race,
  so `develop` sometimes missed the version bump and changelog promotion
  from a release (as happened with `v1.3.0`).
- CI: the GitHub release's notes are now the promoted CHANGELOG.md
  section for that version (via the new `scripts/changelog_notes.py`),
  instead of GitHub's auto-generated list of merged PRs.
- Status Bars: Windows with status bars now utilize them to show status tips
  (tooltips that are in the status bar) to guide the user.
  - Status bars also show important messages.
- Main window: connecting the serial monitor now also disables the board
  select, COM port refresh, open/upload file, and baud rate controls for
  the duration of the connection (previously only **Upload to Board** was
  disabled), and enables the **Send** button only while connected, since
  sending data requires an active connection.

## [1.3.0] - 2026-08-21

### Added

- Application stylesheet (`assets/style.qss`), applied app-wide via
  `QApplication.setStyleSheet()`, giving every window a consistent look
  (colors, borders, hover/pressed/disabled states) sampled from the app
  icon's palette. See the new **Styling** section in the README.
- Automated version-bump and changelog-promotion GitHub Actions
  workflows: `develop` commits bump `pyproject.toml`'s `-devN` prerelease
  suffix automatically, and merges to `main` strip the suffix and promote
  the `[Unreleased]` changelog section to a dated release section.

### Changed

- Main window layout switched to `QGridLayout` so its widgets resize
  themselves to fill the window, instead of being manually resized on
  every resize event, improving responsiveness when scaling the window.

## [1.0.1] - 2026-08-20

### Fixed

- `step_array` progress bar: steps now advance the bar by a fixed count of
  `1` against a maximum of `num_steps - 1`, instead of by
  `100 // num_steps` against an implicit 0-100 range, which could over- or
  under-shoot a full bar depending on `num_steps`. The bar's value is now
  also clamped at its maximum.

## [1.0.0] - 2026-08-20

First stable release — graduates the app out of beta.

### Added

- **Preferences dialog** (**Edit > Preferences...**):
  - **General** tab: override the app's font (family and size) via a font
    picker and size spinner, applied on next app start or reload; **Revert
    to Defaults** restores the bundled Nerd Font at 11pt. The chosen font
    applies to every top-level window, including the CAN Viewer and ELF
    Parser.
  - **Advanced** tab: **Import Settings**/**Export Settings** (read/write
    the whole settings file as an INI, backing up the current file first
    on import) and **Clear All Settings**, moved here from the old Tools
    menu.
- **`sub_settings`** for CLI flashing tools: a further named-preset table,
  selectable via a sub-settings dropdown next to the main settings
  dropdown, whose values merge into the `$variable` substitutions
  available to `custom_settings` argument lists — for per-target values
  (e.g. memory offsets) the fixed variable list can't express.
- **`tool_settings.use_pty`**: runs a CLI flashing tool attached to a real
  Windows pseudo console (ConPTY) instead of a plain pipe, for tools that
  only emit progress/status via Win32 console APIs and would otherwise
  produce no captured output.
- **`tool_settings.stop_on`**: a list of substring markers that force-kill
  a CLI tool's process if it hangs on a blocking prompt after finishing
  its real work, instead of hanging the flash indefinitely.

### Changed

- Stored settings (`QSettings`) are now namespaced under sections (e.g.
  `board_flashing/selected_board` instead of a bare `selected_board`).
  `StoredSettings.transfer_legacy_settings()` runs on every startup to
  migrate any value still under its old flat key, after first backing up
  the whole settings INI file.

## [0.9.0-beta] - 2026-08-19

### Added

- Silent installation and a force-update option for the auto-updater.

### Changed

- Improved installer handling and the app relaunch mechanism after an
  update is applied.

## [0.8.0-beta] - 2026-08-18

### Changed

- Project/version settings housekeeping ahead of the beta line.

## [0.7.1-beta] - 2026-08-18

### Fixed

- Hotfix: the auto-updater compared the PEP 440-normalized version string
  (e.g. `0.7.0b0`) instead of the SEMVER string (`0.7.0-beta`), which
  caused update checks to fail.

## [0.7.0-beta] - 2026-08-18

### Added

- ELF parser tool, with UI integration.
- Windows installer via Inno Setup, plus supporting build tooling and an
  app logo/icon.
- GitHub issue templates (bug report, feature request) and an enhanced
  pull request template.
- MIT License.

### Changed

- README enhanced with Windows installer instructions; copyright notice
  updated.
- Code structure refactored and enhanced across multiple modules.

## [0.6.0-beta] - 2026-08-18

### Added

- CAN viewer tool, integrated into the main application, with USB
  monitoring, CAN logging, and reload support.
- Settings/cache persistence and secure credential storage.
- CI workflows for automated testing and release.
- A pytest suite covering core business logic.

### Changed

- The `Bitrate` enum is now lazy-loaded, so the app no longer crashes when
  CANlib isn't installed.

## [0.5.1-alpha] - 2026-08-17

### Fixed

- Hotfix: a critical crash when retrieving a setting that had never been
  set.

## [0.5.0-alpha] - 2026-08-13

### Added

- GitHub token management and a remote board/flashing-tool config editing
  UI.
- Session state persistence and an in-app reload function.
- Release workflow support for both `main` and `develop` branches, with
  Nuitka compilation caching.

### Fixed

- Incorrect string formatting in the warning log for an unknown flasher
  type.

## [0.4.0-alpha] - 2026-08-12

### Added

- Progress bar support for flashing tools, including regex-based
  detection of hex addresses to drive progress.

## [0.3.1-alpha] - 2026-08-12

### Fixed

- Hotfix: additional logging added, with debug logging enabled to the log
  file, to aid diagnosing field issues.

## [0.3.0-alpha] - 2026-08-12

### Added

- Auto-update functionality, with accompanying logging enhancements.

## [0.2.0-alpha] - 2026-08-11

### Added

- Custom settings presets for flashing tools, with corresponding
  documentation updates.

## [0.1.0-alpha] - 2026-08-11

Initial release.

### Added

- Board configuration files and flashing tool implementations for ESP32
  and AVR targets.
- Custom font support and initial UI layout.
- Support for additional boards and flashing tools, with documentation.
- `FlasherFinder` and `CLIFlashingTool`.
- Flashing tool configuration and UI enhancements.
- Revamped installation instructions, UI components, and support for
  loading configs from external directories.
- GitHub Actions workflow to release on merge to `main`.

### Fixed

- Build output validation before packaging; Nuitka `extra_args` update.
- Streamlined virtual environment activation in the CI workflow.

[Unreleased]: https://github.com/RAMENtheNOODLES/dev-board-flasher/compare/v1.8.4...HEAD
[1.8.4]: https://github.com/RAMENtheNOODLES/dev-board-flasher/compare/v1.8.1...v1.8.4
[1.8.1]: https://github.com/RAMENtheNOODLES/dev-board-flasher/compare/v1.3.0...v1.8.1
[1.3.0]: https://github.com/RAMENtheNOODLES/dev-board-flasher/compare/v1.0.0...v1.3.0
[1.0.1]: https://github.com/RAMENtheNOODLES/dev-board-flasher/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/RAMENtheNOODLES/dev-board-flasher/compare/v0.9.0-beta...v1.0.0
[0.9.0-beta]: https://github.com/RAMENtheNOODLES/dev-board-flasher/compare/v0.8.0-beta...v0.9.0-beta
[0.8.0-beta]: https://github.com/RAMENtheNOODLES/dev-board-flasher/compare/v0.7.1-beta...v0.8.0-beta
[0.7.1-beta]: https://github.com/RAMENtheNOODLES/dev-board-flasher/compare/v0.7.0-beta...v0.7.1-beta
[0.7.0-beta]: https://github.com/RAMENtheNOODLES/dev-board-flasher/compare/v0.6.0-beta...v0.7.0-beta
[0.6.0-beta]: https://github.com/RAMENtheNOODLES/dev-board-flasher/compare/v0.5.1-alpha...v0.6.0-beta
[0.5.1-alpha]: https://github.com/RAMENtheNOODLES/dev-board-flasher/compare/v0.5.0-alpha...v0.5.1-alpha
[0.5.0-alpha]: https://github.com/RAMENtheNOODLES/dev-board-flasher/compare/v0.4.0-alpha...v0.5.0-alpha
[0.4.0-alpha]: https://github.com/RAMENtheNOODLES/dev-board-flasher/compare/v0.3.1-alpha...v0.4.0-alpha
[0.3.1-alpha]: https://github.com/RAMENtheNOODLES/dev-board-flasher/compare/v0.3.0-alpha...v0.3.1-alpha
[0.3.0-alpha]: https://github.com/RAMENtheNOODLES/dev-board-flasher/compare/v0.2.0-alpha...v0.3.0-alpha
[0.2.0-alpha]: https://github.com/RAMENtheNOODLES/dev-board-flasher/compare/v0.1.0-alpha...v0.2.0-alpha
[0.1.0-alpha]: https://github.com/RAMENtheNOODLES/dev-board-flasher/releases/tag/v0.1.0-alpha
