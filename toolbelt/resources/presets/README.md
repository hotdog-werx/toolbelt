# Toolbelt Configuration Presets

Toolbelt provides several curated configuration presets that you can use as
building blocks for your project's tooling setup.

## Available Presets

### Core Presets

- **`@toolbelt:resources/presets/python-core.yaml`** - Essential Python tools
  (Ruff linting and formatting)
- **`@toolbelt:resources/presets/python-typed.yaml`** - Python + type checking
  with BasedPyright
- **`@toolbelt:resources/presets/python-dev.yaml`** - Full Python development
  setup (includes complexity checking and test coverage)
- **`@toolbelt:resources/presets/python-hdw.yaml`** - Hotdog-werx opinionated
  Python style (5-step format process: 80-char format → trailing commas →
  default format → auto-fix → final format)

### Language-Specific Presets

- **`@toolbelt:resources/presets/web.yaml`** - Web development tools (Prettier
  for Markdown, JSON, YAML)
- **`@toolbelt:resources/presets/yaml.yaml`** - YAML formatting with yq

### Opinionated Presets

- **`@toolbelt:resources/presets/python-hdw.yaml`** - Hotdog-werx's opinionated
  Python formatting workflow. This uses a 5-step process that enforces trailing
  commas strategically (only where they make sense) rather than always requiring
  them, creating cleaner diffs and more flexible code style.

### Curated Collections

- **`@toolbelt:resources/presets/recommended.yaml`** - Recommended setup for
  most projects (Python + web tools, using standard formatting)
- **`@toolbelt:resources/presets/hdw.yaml`** - Complete hotdog-werx style
  (Python HDW opinionated formatting + complexity checking + coverage + type
  checking + web tools)

## Usage Examples

### Using Presets in pyproject.toml

```toml
[tool.toolbelt]
include = ["@toolbelt:resources/presets/recommended.yaml"]
```

### Using Presets in toolbelt.yaml

```yaml
include:
  - '@toolbelt:resources/presets/python-core.yaml'
  - '@toolbelt:resources/presets/web.yaml'

# Add your custom overrides
profiles:
  python:
    check_tools:
      - name: 'custom-linter'
        command: 'my-custom-tool'
        args: ['--strict']
        file_handling_mode: 'batch'

variables:
  TB_PROJECT_SOURCE: 'src'
```

### Creating Your Own Configuration

```yaml
# For a simple Python project
include:
  - "@toolbelt:resources/presets/python-core.yaml"

# For a Python project with type checking
include:
  - "@toolbelt:resources/presets/python-typed.yaml"

# For a full-stack web project
include:
  - "@toolbelt:resources/presets/python-dev.yaml"
  - "@toolbelt:resources/presets/web.yaml"
```

## Preset Hierarchy

The presets build on each other:

```
python-core.yaml (base Python tools)
  ↗               ↘
python-typed.yaml  python-strict.yaml
  ↗
python-dev.yaml (includes complexity + coverage)
```

## Variables

Each preset defines sensible defaults for tool versions and project structure:

- `TB_RUFF_VERSION: latest`
- `TB_BASEDPYRIGHT_VERSION: latest`
- `TB_PRETTIER_VERSION: latest`
- `TB_PROJECT_SOURCE: src` (default source directory for coverage)

You can override these in your own configuration:

```yaml
include:
  - '@toolbelt:resources/presets/python-dev.yaml'

variables:
  TB_RUFF_VERSION: '0.1.6' # Pin to specific version
  TB_PROJECT_SOURCE: 'myproject' # Custom source directory
```
