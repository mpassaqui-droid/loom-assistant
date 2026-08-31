#!/usr/bin/env bash
# Rebuilds validator/prebuilt/loom-validate-linux-x86_64 from loom-core's
# CURRENT source (in the private ~/Dev/loom repo — never committed here,
# only the compiled artifact is). Run this after any loom-core change that
# should reach the deployed demo.
#
# Cross-compiles from macOS (any arch) to linux/x86_64 via a musl toolchain,
# since Render (and most hosts) run linux/amd64:
#   brew install messense/macos-cross-toolchains/x86_64-unknown-linux-musl
#   rustup target add x86_64-unknown-linux-musl
set -euo pipefail
cd "$(dirname "$0")/.."

export PATH="/opt/homebrew/opt/x86_64-unknown-linux-musl/bin:$PATH"
cd validator
cargo build --release --target x86_64-unknown-linux-musl
cd ..
mkdir -p validator/prebuilt
cp validator/target/x86_64-unknown-linux-musl/release/loom-validate validator/prebuilt/loom-validate-linux-x86_64
chmod +x validator/prebuilt/loom-validate-linux-x86_64
echo "Rebuilt validator/prebuilt/loom-validate-linux-x86_64"
file validator/prebuilt/loom-validate-linux-x86_64
