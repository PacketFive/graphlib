.PHONY: test lint format

PYTHONPATH := .

test:
	PYTHONPATH=$(PYTHONPATH) pytest tests/

lint:
	mypy mygraphlib/

format:
	black mygraphlib/ tests/