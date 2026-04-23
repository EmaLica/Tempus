#!/usr/bin/env bash
# Development runner — compiles the GSettings schema locally before launching.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

glib-compile-schemas data/
export GSETTINGS_SCHEMA_DIR="$SCRIPT_DIR/data"

python -m tempus "$@"
