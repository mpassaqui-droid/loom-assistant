#!/usr/bin/env bash
# Copies loom-core's source into ./loom-core-src so the Docker build context
# can see it (Docker can't COPY from outside its build context, and loom-core
# lives in the sibling ~/Dev/loom repo). Read-only copy, regenerated each
# time, never commits back to ~/Dev/loom. Run before `docker build`.
set -euo pipefail
cd "$(dirname "$0")/.."
rm -rf loom-core-src
mkdir -p loom-core-src
cp -R "$HOME/Dev/loom/loom-core/Cargo.toml" "$HOME/Dev/loom/loom-core/src" loom-core-src/
echo "Vendored loom-core into ./loom-core-src"
