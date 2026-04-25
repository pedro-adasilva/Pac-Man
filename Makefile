PYTHON ?= python3
VENV_DIR := .venv
VENV_PYTHON := $(VENV_DIR)/bin/python
VENV_PIP := $(VENV_PYTHON) -m pip
WHEEL := ./mazegenerator-00001-py3-none-any.whl

.PHONY: install run debug clean lint lint-strict

$(VENV_DIR)/bin/python:
	$(PYTHON) -m venv $(VENV_DIR)

install: $(VENV_DIR)/bin/python
	$(VENV_PIP) install --upgrade pip
	$(VENV_PIP) install -r requirements.txt
	$(VENV_PIP) install $(WHEEL)

run: install
	$(VENV_PYTHON) pac-man.py config.json

debug: install
	$(VENV_PYTHON) -m pdb pac-man.py config.json

clean:
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	rm -rf .mypy_cache .pytest_cache

lint:
	$(VENV_DIR)/bin/flake8 src tests
	PYTHONPATH=src $(VENV_DIR)/bin/mypy src tests --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict:
	$(VENV_DIR)/bin/flake8 src tests
	PYTHONPATH=src $(VENV_DIR)/bin/mypy src tests --strict
