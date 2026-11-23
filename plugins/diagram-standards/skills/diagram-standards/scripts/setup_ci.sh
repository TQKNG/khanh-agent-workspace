#!/usr/bin/env bash
# usage: setup_ci.sh [docs-repo-root]   installs the diagram export workflow into the docs repo
set -euo pipefail
root="${1:-.}"
here="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$root/.github/workflows" "$root/diagrams/src" "$root/images/diagrams"
cp "$here/ci/export-diagrams.yml" "$root/.github/workflows/export-diagrams.yml"
echo "$root/.github/workflows/export-diagrams.yml"
