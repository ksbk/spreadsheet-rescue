.PHONY: help install dev lint format typecheck test coverage demo clean distclean

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

coverage: ## Run pytest with coverage report
	$(VENV)/bin/pytest tests/ --cov=spreadsheet_rescue --cov-report=term-missing --cov-report=html
	@echo ""
	@echo "HTML coverage report: htmlcov/index.html"

# ── Run ──────────────────────────────────────────────────────────

demo: install ## Run pipeline on example data
	$(SRESCUE) run -i examples/raw_sales.csv --out-dir $(DEMO_DIR)
	@echo ""
	@echo "Output:"
	@ls -lh $(DEMO_DIR)/

version: ## Print tool version
	$(SRESCUE) --version

# ── Cleanup ──────────────────────────────────────────────────────

clean: ## Remove build artifacts, caches, and output
	rm -rf output/ demo/output/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '*.egg-info' -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete 2>/dev/null || true
	rm -rf build/ dist/ .eggs/

distclean: clean ## clean + remove venv
	rm -rf $(VENV)
