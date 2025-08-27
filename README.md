# toolbelt

Format or run checks on files by running tools on them

> NOTE: This is a work in progress. Documentation is being updated to reflect
> the latest changes.

## What Makes Toolbelt Natural

Toolbelt abstracts away the complexity of different tool behaviors into a
unified interface. Once a tool is configured, developers don't need to remember:

- Does this tool take directories or files?
- Does it discover files itself or need them listed?
- Does it edit in-place or output to stdout?
- What are the right flags for this specific tool?

Instead, you just run `tb check python` or `tb format yaml` and toolbelt figures
out how to orchestrate everything properly.

## The Three Execution Modes

Toolbelt handles any file-processing tool through three fundamental approaches:

- **Discovery Mode**: Tools like `ruff check .` or `prettier --check .` that
  naturally discover and process files based on their own logic
- **Per-file Mode**: Tools that work best when given explicit file lists, where
  toolbelt discovers the files and passes them to the tool
- **File Rewriting**: Tools that output formatted content that needs to be
  written back to files

This creates a seamless developer experience - toolbelt becomes the universal
interface to all your development tools, and you don't have to context-switch
between different tool syntaxes and behaviors.

## Offline tools

- `pnpm dlx` => `env NPM_CONFIG_OFFLINE=true tb check prettier`.
- `uvx` => `env UV_OFFLINE=1 tb check python`.

## Configuration Presets and Environment Variables

Toolbelt provides configuration presets that you can include and customize
rather than writing tool configurations from scratch. This approach promotes
reuse and consistency across projects.

### Python Development Preset (`python-dev.yaml`)

The `python-dev.yaml` preset includes a `coverage` profile that runs pytest with
coverage reporting. Instead of overriding the entire configuration, you can
customize it using environment variables:

#### Coverage Environment Variables

- **`TB_PROJECT_SOURCE`** (default: `src`) - Primary source directory to measure
  coverage for
- **`TB_COVERAGE_TARGET`** (default: `tests`) - Directory containing test files
  to run
- **`TB_COVERAGE_EXTRA_ARGS`** (default: empty) - Additional arguments to pass
  to pytest

#### Usage Examples

```bash
# Basic usage with defaults
tb check coverage
# Runs: pytest -v --tb=short --cov=src --cov-report=term-missing --cov-report=html:.coverage-files/htmlcov tests

# Cover a different source directory
TB_PROJECT_SOURCE=toolbelt tb check coverage
# Runs: pytest -v --tb=short --cov=toolbelt --cov-report=term-missing --cov-report=html:.coverage-files/htmlcov tests

# Add extra coverage directories and options
TB_COVERAGE_EXTRA_ARGS="--cov=tests --cov-fail-under=90 --cov-branch" tb check coverage
# Runs: pytest -v --tb=short --cov=src --cov=tests --cov-fail-under=90 --cov-branch --cov-report=term-missing --cov-report=html:.coverage-files/htmlcov tests

# Combine multiple customizations
TB_PROJECT_SOURCE=myapp TB_COVERAGE_TARGET=test_suite TB_COVERAGE_EXTRA_ARGS="--cov=scripts --cov-fail-under=80" tb check coverage
```

#### Dynamic Argument Expansion

The `TB_COVERAGE_EXTRA_ARGS` variable supports **automatic argument
splitting** - if you provide multiple space-separated arguments, they will be
properly split into separate command arguments:

```bash
# This single environment variable:
TB_COVERAGE_EXTRA_ARGS="--cov=lib --cov=scripts --cov-fail-under=85"

# Automatically becomes these separate arguments:
# --cov=lib --cov=scripts --cov-fail-under=85
```

This makes it easy to add multiple coverage directories, set thresholds, enable
branch coverage, or add any other pytest/coverage options without needing to
override the entire tool configuration.

## Tab Completion (argcomplete)

Toolbelt supports tab completion for its CLI using
[argcomplete](https://pypi.org/project/argcomplete/).

### Bash / Zsh

Add this to your shell or `.bashrc` / `.zshrc`:

```bash
eval "$(register-python-argcomplete tb)"
```

After setup, you can use tab completion for all CLI options and arguments.
