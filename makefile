# --------------------------------------------------------------------
# CONFIGURATION & FILE DISCOVERY
# --------------------------------------------------------------------
PYTHON   = python
DESIGNER = pyside6-designer
UIC      = pyside6-uic
RCC      = pyside6-rcc

# Directories
UI_DIR   = ui
SRC_DIR  = src

# Find all separate .ui component files
UI_FILES  := $(wildcard $(UI_DIR)/*.ui)
QRC_FILES := $(wildcard *.qrc)

# Map UI source views to compiled Python modules
PY_UI_FILES  := $(patsubst $(UI_DIR)/%.ui,$(SRC_DIR)/ui_%.py,$(UI_FILES))
PY_R_FILES   := $(patsubst %.qrc,$(SRC_DIR)/%_rc.py,$(QRC_FILES))

# Main executable script
MAIN_APP = $(SRC_DIR)/main.py

# --------------------------------------------------------------------
# TARGET RULES
# --------------------------------------------------------------------
.PHONY: all ui rcc run design clean

# Default: Compiles all individual UI parts and assets
all: ui rcc

# Pattern rule: Compiles each component into its own ui_*.py file
$(SRC_DIR)/ui_%.py: $(UI_DIR)/%.ui
	@mkdir -p $(SRC_DIR)
	$(UIC) $< -o $@

$(SRC_DIR)/%_rc.py: %.qrc
	@mkdir -p $(SRC_DIR)
	$(RCC) $< -o $@

ui: $(PY_UI_FILES)
rcc: $(PY_R_FILES)

# Run the app (Automatically compiles any changed .ui components first)
run: all
	$(PYTHON) $(MAIN_APP)

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
