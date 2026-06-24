#!/usr/bin/env bash
# Stage the PyInstaller-built GBT sidecar into app/src-tauri/binaries/
# with the target-triple naming convention required by Tauri v2.
# Usage:
#   bash scripts/tauri/stage-gbt-sidecar.sh [target-triple]
#
# If no target triple is provided, the script tries to infer it from uname.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TARGET="${1:-}"

if [ -z "$TARGET" ]; then
  OS="$(uname -s)"
  ARCH="$(uname -m)"
  case "$OS" in
    Linux)     TARGET="x86_64-unknown-linux-gnu" ;;
    Darwin)
      case "$ARCH" in
        arm64) TARGET="aarch64-apple-darwin" ;;
        x86_64) TARGET="x86_64-apple-darwin" ;;
        *) echo "Unsupported macOS arch: $ARCH"; exit 1 ;;
      esac
      ;;
    MINGW*|MSYS*|CYGWIN*)
      TARGET="x86_64-pc-windows-msvc"
      ;;
    *)
      echo "Unsupported OS: $OS"; exit 1 ;;
  esac
fi

SRC_EXT=""
DST_EXT=""
case "$TARGET" in
  *windows*) SRC_EXT=".exe"; DST_EXT=".exe" ;;
esac

SRC="$ROOT/dist/gbt-sidecar$SRC_EXT"
DST_DIR="$ROOT/app/src-tauri/binaries"
DST="$DST_DIR/gbt-sidecar-$TARGET$DST_EXT"

if [ ! -f "$SRC" ]; then
  echo "Sidecar binary not found: $SRC"
  echo "Run: python scripts/tauri/build-gbt-sidecar.py"
  exit 1
fi

mkdir -p "$DST_DIR"
cp "$SRC" "$DST"
echo "Staged: $DST"
