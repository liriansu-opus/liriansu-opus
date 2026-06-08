ensure:
	uv sync --extra dev

fmt: ensure
	uv run ruff check --fix .
	uv run ruff format .

lint: ensure
	uv run ruff check .
	uv run ruff format --check .

build: ensure
	uv build

# Single source of truth for the version is pyproject.toml; uv rewrites it.
bump-patch:
	uv version --bump patch

bump-minor:
	uv version --bump minor

test-install: build
	uv venv /tmp/test-lki
	uv pip install --python /tmp/test-lki dist/*.whl
	/tmp/test-lki/bin/lki --help
	rm -rf /tmp/test-lki

clean:
	rm -rf dist/ build/ *.egg-info/ .ruff_cache/
