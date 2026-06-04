.PHONY: install dev test lint fmt run eval clean

PYTHON ?= python3

install:
	$(PYTHON) -m pip install -e .

dev:
	$(PYTHON) -m pip install -e ".[dev]"

test:
	$(PYTHON) -m pytest tests/ -q

lint:
	$(PYTHON) -m ruff check src/ evals/ protocols/ tests/

fmt:
	$(PYTHON) -m ruff format src/ evals/ protocols/ tests/

# Example engagement. Requires a provider key in the environment (see .env.example).
run:
	$(PYTHON) -m quorum.cli --region CN --industry "electric vehicles" --depth scan --out report.md

# Score an existing report with the quality scorecard.
eval:
	$(PYTHON) -c "import json,sys; sys.path.insert(0,'.'); from evals.scorecard import heuristic_metrics; print(json.dumps(heuristic_metrics(open('report.md').read()), indent=2))"

clean:
	rm -rf .pytest_cache .ruff_cache build dist *.egg-info
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
