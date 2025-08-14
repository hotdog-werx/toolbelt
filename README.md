# toolbelt

Format or run checks on files by running tools on them

> NOTE: This is a work in progress. Documentation is being updated to reflect the latest changes.

## What Makes Toolbelt Natural

Toolbelt abstracts away the complexity of different tool behaviors into a unified interface. Once a tool is configured, developers don't need to remember:

- Does this tool take directories or files?
- Does it discover files itself or need them listed?
- Does it edit in-place or output to stdout?
- What are the right flags for this specific tool?

Instead, you just run `tb check python` or `tb format yaml` and toolbelt figures out how to orchestrate everything properly.

## The Three Execution Modes

Toolbelt handles any file-processing tool through three fundamental approaches:

- **Discovery Mode**: Tools like `ruff check .` or `prettier --check .` that naturally discover and process files based on their own logic
- **Per-file Mode**: Tools that work best when given explicit file lists, where toolbelt discovers the files and passes them to the tool
- **File Rewriting**: Tools that output formatted content that needs to be written back to files

This creates a seamless developer experience - toolbelt becomes the universal interface to all your development tools, and you don't have to context-switch between different tool syntaxes and behaviors.

## Offline tools

- `pnpm dlx` => `env NPM_CONFIG_OFFLINE=true tb check prettier`.
- `uvx` => `env UV_OFFLINE=1 tb check python`.
