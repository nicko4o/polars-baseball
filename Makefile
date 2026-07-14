ACT_FLAGS :=
LOG_LEVEL := INFO
MYPY_RUN_AGAINST_DEFAULT := polars_baseball/
MYPY_RUN_AGAINST := $(MYPY_RUN_AGAINST_DEFAULT)
ONLY_MODIFIED := 1
TEST_RUN_AGAINST := tests/polars_baseball
TEST_FLAGS := -n auto


ifeq ($(LOG_LEVEL), DEBUG)
	TEST_FLAGS += -v --log-cli-level=DEBUG
endif

ifeq ($(ONLY_MODIFIED), 1)
	_MODIFIED_FILES := $(shell git status --porcelain | awk '{print $$2}' | grep '\.py$$')
	_EXISTING_MODIFIED_FILES := $(wildcard $(_MODIFIED_FILES))
	_UNIQUE_MODIFIED_FILES := $(shell echo $(_EXISTING_MODIFIED_FILES) | sort | uniq)
	ifeq ($(MYPY_RUN_AGAINST), $(MYPY_RUN_AGAINST_DEFAULT))
		ifneq ($(_UNIQUE_MODIFIED_FILES),)
			MYPY_RUN_AGAINST := $(_UNIQUE_MODIFIED_FILES)
		endif
	endif
endif

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

# The test-github-actions is here to allow any local developer to test the GitHub actions on their code
# before pushing and creating a PR. Just install act from https://github.com/nektos/act and run
# make test-github-actions
ACT_EXISTS := $(shell act --help 2> /dev/null)

ifeq ($(ACT_EXISTS),)
test-github-actions:
	@echo "Testing GitHub actions requires act to be installed. See: https://github.com/nektos/act"
else
test-github-actions:
	act pull_request -P ubuntu-latest=nektos/act-environments-ubuntu:18.04 $(ACT_FLAGS)
endif
