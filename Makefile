.PHONY: help install dev lint format typecheck test coverage demo build twine-check smoke-install customer-pack preflight release-tag clean distclean

VENV      := .venv
PYTHON    := $(VENV)/bin/python
PIP       := $(VENV)/bin/pip
SRESCUE   := $(VENV)/bin/srescue
DEMO_DIR  := demo/output

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

# ── Setup ────────────────────────────────────────────────────────

$(VENV)/bin/activate:
	python3 -m venv $(VENV)

install: $(VENV)/bin/activate ## Install package (editable) into venv
	$(PIP) install -e .

dev: $(VENV)/bin/activate ## Install package + dev tools (ruff, mypy, pytest, build, twine)
	$(PIP) install -e ".[dev]" 2>/dev/null || $(PIP) install -e .
	$(PIP) install ruff mypy pytest build twine

# ── Quality ──────────────────────────────────────────────────────

lint: ## Run ruff linter
	$(VENV)/bin/ruff check src/ tests/

format: ## Auto-format with ruff
	$(VENV)/bin/ruff format src/ tests/
	$(VENV)/bin/ruff check --fix src/ tests/

typecheck: ## Run mypy type checks
	$(VENV)/bin/mypy src/spreadsheet_rescue/

test: ## Run pytest
	$(VENV)/bin/pytest tests/ -v

coverage: ## Run pytest with coverage report
	$(VENV)/bin/pytest tests/ --cov=spreadsheet_rescue --cov-report=term-missing --cov-report=html
	@echo ""
	@echo "HTML coverage report: htmlcov/index.html"

# ── Run ──────────────────────────────────────────────────────────

demo: install ## Run pipeline on demo dataset
	./scripts/demo.sh
	@echo ""
	@echo "Output:"
	@ls -lh $(DEMO_DIR)/

build: ## Build source and wheel distributions
	uv run --with build python -m build

twine-check: build ## Validate built distributions
	uv run --with twine twine check dist/*

smoke-install: ## Build wheel, install in clean venv, and run demo smoke
	uv run --with build bash ./scripts/smoke_install.sh

customer-pack: ## Build customer demo pack zip for buyer evaluation
	uv run python ./scripts/build_customer_demo_pack.py
	@echo "Pack: dist/customer-demo-pack.zip"

preflight: ## Run release preflight checks without bumping/tagging
	./scripts/preflight.sh

release-tag: ## Create and push a release tag (VERSION=v0.1.3)
	@test -n "$(VERSION)" || (echo "VERSION is required (e.g. make release-tag VERSION=v0.1.3)" && exit 1)
	git tag -a $(VERSION) -m "$(VERSION)"
	git push origin $(VERSION)

version: ## Print tool version
	$(SRESCUE) --version

# ── Cleanup ──────────────────────────────────────────────────────

clean: ## Remove build artifacts, caches, and output
	rm -rf output/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '*.egg-info' -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete 2>/dev/null || true
	rm -rf build/ dist/ .eggs/

distclean: clean ## clean + remove venv
	rm -rf $(VENV)
