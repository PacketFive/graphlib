.PHONY: test lint format visualize-nx precommit

PYTHONPATH := .

test:
	PYTHONPATH=$(PYTHONPATH) pytest tests/

lint:
	mypy mygraphlib/

format:
	black mygraphlib/ tests/

visualize-nx:
	PYTHONPATH=$(PYTHONPATH) python visualize_with_networkx.py

precommit:
	black mygraphlib/ tests/ visualize_with_*.py
	mypy mygraphlib/ tests/ visualize_with_*.py