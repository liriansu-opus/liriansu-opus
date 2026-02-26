PYTHON ?= python3
VENV ?= .venv
VENV_PYTHON := $(VENV)/bin/python
VENV_RUFF := $(VENV)/bin/ruff

ensure:
	$(PYTHON) -m venv $(VENV)
	$(VENV_PYTHON) -m pip install -U pip
	$(VENV_PYTHON) -m pip install -e ".[dev]"

fmt: ensure
	$(VENV_RUFF) check --fix .
	$(VENV_RUFF) format .

lint: ensure
	$(VENV_RUFF) check .
	$(VENV_RUFF) format --check .

build: ensure
	$(VENV_PYTHON) -m build

test-install: build
	$(PYTHON) -m venv /tmp/test-lki
	/tmp/test-lki/bin/pip install dist/*.whl
	/tmp/test-lki/bin/lki --help
	rm -rf /tmp/test-lki

clean:
	rm -rf dist/ build/ *.egg-info/
