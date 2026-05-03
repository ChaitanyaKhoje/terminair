.DEFAULT_GOAL := help

PYTHON ?= python3.11
VENV ?= .venv
VENV_PYTHON := $(VENV)/bin/python
SETUP_STAMP := $(VENV)/.terminair-installed
AIRFLOW_REPO_URL ?= https://github.com/ChaitanyaKhoje/airflow-dag-template.git
AIRFLOW_DIR ?= .demo/airflow-dag-template
TERMINAIR_URL ?= http://localhost:8080
TERMINAIR_USER ?= admin
TERMINAIR_PASSWORD ?= admin
AIRFLOW_INIT_SENTINEL ?= $(AIRFLOW_DIR)/.airflow-dag-template-initialized

.PHONY: help setup airflow-bootstrap airflow-up airflow-down demo test

help:
	@printf "Targets:\n"
	@printf "  setup       Install Terminair in editable dev mode\n"
	@printf "  demo        Bootstrap Airflow, start it, and launch Terminair\n"
	@printf "  airflow-up  Start the cached example Airflow stack\n"
	@printf "  airflow-down Stop the cached example Airflow stack\n"
	@printf "  test        Run the test suite\n"

setup: $(SETUP_STAMP)

$(SETUP_STAMP): pyproject.toml
	@if ! command -v "$(PYTHON)" >/dev/null 2>&1; then \
		printf "Python 3.11+ is required. Set PYTHON=/path/to/python3.11 or install python3.11.\n"; \
		exit 1; \
	fi
	@if [ ! -x "$(VENV_PYTHON)" ]; then \
		$(PYTHON) -m venv "$(VENV)"; \
	fi
	$(VENV_PYTHON) -m pip install -e ".[dev]"
	@touch "$(SETUP_STAMP)"

airflow-bootstrap:
	@if [ ! -d "$(AIRFLOW_DIR)/.git" ]; then \
		mkdir -p "$(dir $(AIRFLOW_DIR))"; \
		git clone --depth 1 "$(AIRFLOW_REPO_URL)" "$(AIRFLOW_DIR)"; \
	fi

airflow-up:
	$(MAKE) airflow-bootstrap
	@if [ ! -f "$(AIRFLOW_INIT_SENTINEL)" ]; then \
		cd "$(AIRFLOW_DIR)" && docker compose up airflow-init && touch ".airflow-dag-template-initialized"; \
	fi
	cd "$(AIRFLOW_DIR)" && docker compose up -d
	@printf "Airflow is running at http://localhost:8080 (admin/admin)\n"

airflow-down:
	@if [ -d "$(AIRFLOW_DIR)" ]; then \
		cd "$(AIRFLOW_DIR)" && docker compose down; \
	else \
		printf "No cached Airflow stack found at %s\n" "$(AIRFLOW_DIR)"; \
	fi

demo: setup airflow-up
	TERMINAIR_PASSWORD="$${TERMINAIR_PASSWORD:-$(TERMINAIR_PASSWORD)}" $(VENV_PYTHON) -m terminair --url "$(TERMINAIR_URL)" --user "$(TERMINAIR_USER)"

test: setup
	$(VENV_PYTHON) -m pytest terminair/tests/ -v
