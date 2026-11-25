.PHONY: fmt lint test

fmt:
	uvx ruff check --fix .
	uvx ruff format .

lint:
	uvx ruff check .
	uvx ruff format --check .

test:
	python3 -m unittest discover -s tests -v
