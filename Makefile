.PHONY: fmt lint test test-sidebar

fmt:
	uvx ruff check --fix .
	uvx ruff format .

lint:
	uvx ruff check .
	uvx ruff format --check .

test: test-sidebar
	python3 -m unittest discover -s tests -v

test-sidebar:
	node --test tests/test_cmux_attention.cjs
