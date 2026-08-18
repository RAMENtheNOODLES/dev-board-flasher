# --------------------------------------------------------------------
# CONFIGURATION & FILE DISCOVERY
# --------------------------------------------------------------------
PYTHON   = python
DESIGNER = pyside6-designer
UIC      = pyside6-uic
RCC      = pyside6-rcc
DEPLOY   = pyside6-deploy
RELOADIUM = reloadium
ISCC     = ISCC

# Directories
UI_DIR    = ui
QRC_DIR   = assets
SRC_DIR   = src
BUILD_DIR = build
SPEC_FILE = $(SRC_DIR)/pysidedeploy.spec

# Find all separate .ui component files
UI_FILES  := $(wildcard $(UI_DIR)/*.ui)
QRC_FILES := $(wildcard $(QRC_DIR)/*.qrc)

# Map UI source views to compiled Python modules
PY_UI_FILES  := $(patsubst $(UI_DIR)/%.ui,$(SRC_DIR)/ui_%.py,$(UI_FILES))
PY_R_FILES   := $(patsubst $(QRC_DIR)/%.qrc,$(SRC_DIR)/%_rc.py,$(QRC_FILES))

# Main executable script
MAIN_APP = $(SRC_DIR)/main.py

# --------------------------------------------------------------------
# TARGET RULES
# --------------------------------------------------------------------
.PHONY: all ui rcc run test ruff ruff-fixall design compile installer project-files clean

# Default: Compiles all individual UI parts and assets
all: ui rcc project-files

# Pattern rule: Compiles each component into its own ui_*.py file
$(SRC_DIR)/ui_%.py: $(UI_DIR)/%.ui
	@mkdir -p $(SRC_DIR)
	$(UIC) $< -o $@

$(SRC_DIR)/%_rc.py: $(QRC_DIR)/%.qrc
	@mkdir -p $(SRC_DIR)
	$(RCC) $< -o $@

ui: $(PY_UI_FILES)
rcc: $(PY_R_FILES)

# Run the app (Automatically compiles any changed .ui components first)
run: all
	$(PYTHON) $(MAIN_APP)

# Run the app with reloadium, which hot_reloads the app on any standard code changes
# Does not work with Python versions >=3.11
dev_run: all
	$(RELOADIUM) run $(MAIN_APP)

# --------------------------------------------------------------------
# TESTS
# --------------------------------------------------------------------
# Runs the full test suite (tests/unit + tests/integration). Requires the
# dev extras: pip install -e ".[dev]"
test:
	$(PYTHON) -m pytest -q

# --------------------------------------------------------------------
# LINTING
# --------------------------------------------------------------------
# Not run by any other target, and not a CI gate (see tests.yml's
# report-only lint step) - the existing codebase has a large pre-existing
# violation count under ruff's default rules. Run manually to see current
# findings; requires the dev extras: pip install -e ".[dev]"
ruff:
	$(PYTHON) -m ruff check .

# Same as `ruff`, but applies every auto-fixable violation in place instead
# of just reporting them. Still standalone/manual only.
ruff-fixall:
	$(PYTHON) -m ruff check --fix .

# --------------------------------------------------------------------
# STANDALONE EXECUTABLE
# --------------------------------------------------------------------
# Compiles a standalone executable from the app (recompiles UI/assets first)
# Output directory is controlled by exec_directory in src/pysidedeploy.spec
compile: all
	@mkdir -p $(BUILD_DIR)
	$(DEPLOY) $(MAIN_APP) -c $(SPEC_FILE)

# --------------------------------------------------------------------
# WINDOWS INSTALLER
# --------------------------------------------------------------------
# Builds the standalone exe, then wraps it in an Inno Setup installer.
# AppVersion is read from pyproject.toml (the same way the release workflow
# does) and passed to ISCC so scripts/installer.iss can't drift out of sync
# with the version actually being packaged. Requires Inno Setup's ISCC.exe
# to be on PATH.
installer: compile
	$(ISCC) "/DAppVersion=$(shell $(PYTHON) -c "import tomllib; print(tomllib.load(open('pyproject.toml', 'rb'))['project']['version'])")" scripts/installer.iss

# --------------------------------------------------------------------
# PROJECT FILE LIST
# --------------------------------------------------------------------
# Regenerates the [tool.pyside6-project] files list in pyproject.toml
# from the .py/.ui/.qrc files actually on disk.
project-files:
	$(PYTHON) scripts/sync_project_files.py

# --------------------------------------------------------------------
# WORKFLOW DESIGNER RULE
# --------------------------------------------------------------------
# Opens all UI files together. Recompiles them instantly upon closing Designer.
design:
	@if [ -z "$(UI_FILES)" ]; then \
		echo "No .ui files found in the '$(UI_DIR)' directory!"; \
		$(DESIGNER); \
	else \
		echo "Opening separated components in PySide6 Designer..."; \
		$(DESIGNER) $(UI_FILES); \
		echo "Designer closed. Auto-recompiling all UI modifications..."; \
		$(MAKE) all; \
	fi

clean:
	rm -f $(SRC_DIR)/ui_*.py
	rm -f $(SRC_DIR)/*_rc.py
	find . -type d -name "__pycache__" -exec rm -rf {} +
