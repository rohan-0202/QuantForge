dev:
	uv venv 
	uv pip install --upgrade pip
	uv sync
	uv run pre-commit install

clean-venv:
	rm -rf .venv

recreate-venv: clean-venv dev
	@echo "Virtual environment has been recreated."
	@echo "Run this command in your shell: source .venv/bin/activate"


	

