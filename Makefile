 .PHONY: test clean build release publish-pypi
#################################################################################
# GLOBALS                                                                       #
#################################################################################

PROJECT_DIR := $(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))
PYTHON_INTERPRETER = python3

ifeq (,$(shell which conda))
HAS_CONDA=False
else
HAS_CONDA=True
endif

#################################################################################
# COMMANDS                                                                      #
#################################################################################

## Install package
local:
	rm -rf dist build */*.egg-info *.egg-info
	$(PYTHON_INTERPRETER) setup.py sdist
	pip install -e . --no-cache-dir

install:
	rm -rf dist build */*.egg-info *.egg-info
	$(PYTHON_INTERPRETER) setup.py sdist
	pip install . --no-cache-dir
	
publish-pypi:
	rm -rf dist build */*.egg-info *.egg-info
	$(PYTHON_INTERPRETER) setup.py sdist bdist_wheel
	twine upload dist/*

release:
	bash scripts/release.sh $(VERSION)
	$(MAKE) publish-pypi

format:
	black src/photompy/*
	
lint: format
	flake8 --ignore=E114,E116,E117,E231,E266,E303,E501,W293,W291,W503 src/photompy/*

## Remove compiled python files
clean:
	@echo "Cleaning directory..."
	@find . -type f -name "*.py[co]" -delete
	@find . -type d -name "__pycache__" -delete
	@find . -type f -name "*~" -delete
	@find . -type f -name "*.kate-swp" -delete
	@echo "Done"

test:
	$(PYTHON_INTERPRETER) -m pytest tests/ -v
	
all: install test clean