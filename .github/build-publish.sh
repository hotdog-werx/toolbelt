#!/usr/bin/env bash
set -exuo pipefail

# VERSION must be provided as first argument
if [ $# -lt 1 ]; then
  echo "Usage: $0 <VERSION> (with PYPI_TOKEN set in environment)" >&2
  exit 1
fi
VERSION="$1"

# PYPI_TOKEN must be set in environment
if [ -z "${PYPI_TOKEN:-}" ]; then
  echo "PYPI_TOKEN must be set in environment. Example: PYPI_TOKEN=... $0 <VERSION>" >&2
  exit 1
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
