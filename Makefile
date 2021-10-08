ensure:
	pipenv sync --dev
	pipenv clean
	pipenv run python -m pip install -U pip setuptools

fmt:
	@isort .
	@black -l 120 .

lint:
	isort --check .
	black -l 120 --check .
