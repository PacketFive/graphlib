.PHONY: test lint format visualize

PYTHONPATH := .

test:
	PYTHONPATH=$(PYTHONPATH) pytest tests/

lint:
	mypy mygraphlib/

format:
	black mygraphlib/ tests/

visualize-nx:
	PYTHONPATH=$(PYTHONPATH) python visualize_with_networkx.py