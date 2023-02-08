.PHONY: clean clean-test clean-pyc clean-build clean-reports clean-temp clean-other docs help
.DEFAULT_GOAL := help

SHELL := /bin/bash -o pipefail -o errexit

CONDA_ENV_NAME ?= finder

define BROWSER_PYSCRIPT
import os, webbrowser, sys

from urllib.request import pathname2url

webbrowser.open("file://" + pathname2url(os.path.abspath(sys.argv[1])))
endef
export BROWSER_PYSCRIPT

define PRINT_HELP_PYSCRIPT
import re, sys

for line in sys.stdin:
	match = re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$', line)
	if match:
		target, help = match.groups()
		print("%-20s %s" % (target, help))
endef
export PRINT_HELP_PYSCRIPT

BROWSER := python -c "$$BROWSER_PYSCRIPT"

clean: clean-build clean-cov clean-docs clean-pyc clean-test clean-reports clean-temp clean-other ## remove all build, test, coverage and Python artifacts

clean-cov:
	@rm -rf .coverage
	@rm -rf htmlcov
	@rm -rf reports/{*.html,*.png,*.js,*.css,*.json}
	@rm -rf pytest.xml
	@rm -rf pytest-coverage.txt

clean-build: ## remove build artifacts
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -f {} +

clean-pyc: ## remove Python file artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test: ## remove test and coverage artifacts
	rm -fr .tox/
	rm -f .coverage
	rm -fr htmlcov/
	rm -fr .pytest_cache

clean-reports: ## remove test and coverage artifacts
	rm -fr reports/*.md

clean-temp: ## remove test and coverage artifacts
	rm -fr temp/tmp.txt
	rm -fr tmp.txt

clean-other:
	rm -fr *.prof
	rm -fr profile.html profile.json

help:
	@python -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)

environment:       ## Handles environment creation
	conda env create -f environment.yaml --name $(CONDA_ENV_NAME) --force
	conda run --name $(CONDA_ENV_NAME) pip install -e .

format-black:
	@black .
format-isort:
	@isort .
lint-black:
	@black . --check
lint-isort:
	@isort . --check
lint-flake8:
	@flake8 .
lint-mypy:
	@mypy ./finder
lint-mypy-report:
	@mypy ./finder --html-report ./mypy_html
format: format-black format-isort
lint: lint-black lint-isort lint-flake8 lint-mypy

pre-commit:        ## Runs pre-commit against files
	pre-commit run --all-files

tests:
	@pytest
coverage: ## check code coverage quickly with the default Python
	coverage run --source . -m pytest
	coverage report -m
	coverage html
	$(BROWSER) htmlcov/index.html
test-cov: ## run tests with coverage
	pytest --cov=finder --cov-report term-missing --cov-report=html
tests-cov-fail:
	@pytest --cov=finder --cov-report term-missing --cov-report=html --cov-fail-under=80
test-all: ## run tests on every Python version with tox
	tox

release: dist ## package and upload a release
	twine upload dist/*

dist: clean ## builds source and wheel package
	python -m build
	ls -l dist

install: clean ## install the package to the active Python's site-packages
	pip install .

dev: clean  ## install the package's development version
	pip install -e .
