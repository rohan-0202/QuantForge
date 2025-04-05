
# The following targets are for setting up and maintaining the dev environment

dev:
	uv venv 
	uv pip install --upgrade pip
	uv sync
	uv run pre-commit install

clean-venv:
	rm -rf .venv

lint-fix:
	uv run ruff check --fix

test:
	uv run pytest

recreate-venv: clean-venv dev
	@echo "Virtual environment has been recreated."
	@echo "Run this command in your shell: source .venv/bin/activate"

# The following targets are for getting yfinance data

get_data:
	uv run python src/quantforge/db/create_database.py
	uv run python src/quantforge/db/data_insertion.py

get_data_for_ticker:
	$(eval ticker=$(word 2,$(MAKECMDGOALS)))
	uv run python src/quantforge/db/create_database.py
	uv run python src/quantforge/db/data_insertion.py --ticker $(ticker)


