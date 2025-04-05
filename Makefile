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


	

