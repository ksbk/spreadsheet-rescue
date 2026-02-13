.PHONY: help install dev lint format typecheck test demo clean distclean

VENV      := .venv
PYTHON    := $(VENV)/bin/python
PIP       := $(VENV)/bin/pip
SRESCUE   := $(VENV)/bin/srescue
DEMO_DIR  := output/demo_run

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

# ── Setup ────────────────────────────────────────────────────────

$(VENV)/bin/activate:
	python3 -m venv $(VENV)

install: $(VENV)/bin/activate ## Install package (editable) into venv
	$(PIP) install -e .

dev: $(VENV)/bin/activate ## Install package + dev tools (ruff, mypy, pytest)
	$(PIP) install -e ".[dev]" 2>/dev/null || $(PIP) install -e .
	$(PIP) install ruff mypy pytest

# ── Quality ──────────────────────────────────────────────────────

lint: ## Run ruff linter
	$(VENV)/bin/ruff check src/

format: ## Auto-format with ruff
	$(VENV)/bin/ruff format src/
	$(VENV)/bin/ruff check --fix src/

typecheck: ## Run mypy type checks
	$(VENV)/bin/mypy src/spreadsheet_rescue/

test: ## Run pytest
	$(VENV)/bin/pytest tests/ -v

# ── Run ──────────────────────────────────────────────────────────

demo: install ## Run pipeline on example data
	$(SRESCUE) run -i examples/raw_sales.csv --out-dir $(DEMO_DIR)
	@echo ""
	@echo "Output:"
	@ls -lh $(DEMO_DIR)/

version: ## Print tool version
	$(SRESCUE) --version

# ── Cleanup ──────────────────────────────────────────────────────

clean: ## Remove output directory
	rm -rf output/
	rm -rf .mypy_cache/ 2>/dev/null || true
	rm -rf src/__pycache__/ 2>/dev/null || true

distclean: clean ## Remove output + venv + build artifacts
	rm -rf $(VENV) build/ dist/ *.egg-info src/*.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
