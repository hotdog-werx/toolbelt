#!/usr/bin/env bash
set -euo pipefail
set -x

# Manual publishing script for now
VERSION=0.0.1

# Allow token via env or first positional argument
if [ -z "${PYPI_TOKEN:-}" ]; then
  if [ $# -lt 1 ]; then
    echo "PYPI_TOKEN not set. Usage: PYPI_TOKEN=... $0  OR  $0 <PYPI_TOKEN>" >&2
    exit 1
  fi
  PYPI_TOKEN="$1"
fi

# Clean previous build artifacts to avoid publishing stale files
if [ -d dist ]; then
  rm -rf dist
fi

uvx hatch version "${VERSION}"
uv build --no-sources

export UV_PUBLISH_USERNAME=__token__
export UV_PUBLISH_PASSWORD="${PYPI_TOKEN}"
uv publish
