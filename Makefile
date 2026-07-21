.PHONY: help install mypy vulture test validate-cache test-github-actions

# ------------------------------------------------------------------------------
# Configuration & Variables
# ------------------------------------------------------------------------------
ACT_FLAGS :=
LOG_LEVEL := INFO
MYPY_RUN_AGAINST_DEFAULT := polars_baseball/
MYPY_RUN_AGAINST := $(MYPY_RUN_AGAINST_DEFAULT)
ONLY_MODIFIED := 1
TEST_RUN_AGAINST := tests/polars_baseball
TEST_FLAGS := -n auto

# ------------------------------------------------------------------------------
# Dynamic Behavior Logic
# ------------------------------------------------------------------------------
ifeq ($(LOG_LEVEL), DEBUG)
	TEST_FLAGS += -v --log-cli-level=DEBUG
endif

ifeq ($(ONLY_MODIFIED), 1)
	_MODIFIED_FILES := $(shell git status --porcelain | awk '{print $$NF}' | grep '\.py$$')
	_EXISTING_MODIFIED_FILES := $(wildcard $(_MODIFIED_FILES))
	_UNIQUE_MODIFIED_FILES := $(shell echo $(_EXISTING_MODIFIED_FILES) | sort | uniq)
	ifeq ($(MYPY_RUN_AGAINST), $(MYPY_RUN_AGAINST_DEFAULT))
		ifneq ($(_UNIQUE_MODIFIED_FILES),)
			MYPY_RUN_AGAINST := $(_UNIQUE_MODIFIED_FILES)
		endif
	endif
endif

# ------------------------------------------------------------------------------
# Targets
# ------------------------------------------------------------------------------
help:
	@echo "Available Makefile targets:"
	@echo "  install              Install dependencies via uv"
	@echo "  mypy                 Run static type check (supports ONLY_MODIFIED=1)"
	@echo "  vulture              Run dead code detection"
	@echo "  test                 Run pytest with coverage and parallel workers"
	@echo "  validate-cache       Validate cache structure (runs install first)"
	@echo "  test-github-actions  Run GitHub Actions workflows locally via act"

install:
	uv sync --locked --all-extras

mypy:
	uv run mypy $(MYPY_RUN_AGAINST)

vulture:
	uv run vulture polars_baseball tests --config pyproject.toml

test:
	uv run pytest $(TEST_RUN_AGAINST) $(TEST_FLAGS) --doctest-modules --cov=polars_baseball --cov-report term-missing

validate-cache: install
	uv run python ./scripts/validate_cache.py

# Local GitHub Actions runner validation
ACT_EXISTS := $(shell act --help 2> /dev/null)

ifeq ($(ACT_EXISTS),)
test-github-actions:
	@echo "Testing GitHub actions requires act to be installed. See: https://github.com/nektos/act"
else
test-github-actions:
	act pull_request -P ubuntu-latest=catthehacker/ubuntu:act-latest $(ACT_FLAGS)
endif

