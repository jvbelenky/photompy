 .PHONY: test clean
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
install:
	$(PYTHON_INTERPRETER) setup.py sdist
	pip install .

## Lint using flake8 and black
lint:
	black ies_utils
	flake8 ies_utils

## Remove compiled python files
clean:
	@echo "Cleaning directory..."
	@find . -type f -name "*.py[co]" -delete
	@find . -type d -name "__pycache__" -delete
	@find . -type f -name "*~" -delete
	@find . -type f -name "*.kate-swp" -delete
	@echo "Done"

## Try the example usage
test: 
	$(PYTHON_INTERPRETER) tests/example_usage.py tests/LLIA001477-003.ies

all: install test clean