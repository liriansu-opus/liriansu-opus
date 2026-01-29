ensure:
	uv pip install --system -e ".[dev]"

fmt:
	@ruff check --fix .
	@ruff format .

lint:
	ruff check .
	ruff format --check .

build:
	python -m build

test-install:
	python -m venv /tmp/test-lki
	/tmp/test-lki/bin/pip install dist/*.whl
	/tmp/test-lki/bin/lki --help
	rm -rf /tmp/test-lki

clean:
	rm -rf dist/ build/ *.egg-info/
