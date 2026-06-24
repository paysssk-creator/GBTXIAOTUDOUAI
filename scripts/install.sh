#!/usr/bin/env bash
# GBT AI Workstation installer (macOS/Linux)
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/paysssk-creator/GBTXIAOTUDOUAI/main/scripts/install.sh | bash

set -euo pipefail

REPO="paysssk-creator/GBTXIAOTUDOUAI"
LATEST_API="https://api.github.com/repos/${REPO}/releases/latest"

log_info() { echo "→ $*"; }
log_ok() { echo "✓ $*"; }
log_err() { echo "✗ $*" >&2; }

command -v curl >/dev/null 2>&1 || { log_err "curl is required"; exit 1; }
command -v mktemp >/dev/null 2>&1 || { log_err "mktemp is required"; exit 1; }

OS_RAW="$(uname -s)"
ARCH_RAW="$(uname -m)"

TARGET=""
EXT=""
case "$OS_RAW" in
  Linux)
    TARGET="x86_64-unknown-linux-gnu"
    EXT="AppImage"
    ;;
  Darwin)
    case "$ARCH_RAW" in
      arm64) TARGET="aarch64-apple-darwin" ;;
      x86_64) TARGET="x86_64-apple-darwin" ;;
      *) log_err "Unsupported macOS arch: $ARCH_RAW"; exit 1 ;;
    esac
    EXT="dmg"
    ;;
  *)
    log_err "Unsupported OS: $OS_RAW"; exit 1 ;;
esac

log_info "Detecting latest release..."
RELEASE_JSON="$(curl -fsSL "$LATEST_API")"
VERSION="$(echo "$RELEASE_JSON" | grep -o '"tag_name": "[^"]*"' | head -1 | cut -d'"' -f4)"
[ -z "$VERSION" ] && { log_err "Could not determine latest version"; exit 1; }
log_info "Latest version: $VERSION"

ASSET_NAME="gbt-app_${VERSION#v}_${TARGET}.${EXT}"
ASSET_URL="https://github.com/${REPO}/releases/download/${VERSION}/${ASSET_NAME}"
SUMS_URL="https://github.com/${REPO}/releases/download/${VERSION}/checksums.txt"

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

log_info "Downloading $ASSET_NAME..."
curl -fSL -o "$TMP_DIR/$ASSET_NAME" "$ASSET_URL" || { log_err "Download failed"; exit 1; }

if curl -fsSL -o "$TMP_DIR/checksums.txt" "$SUMS_URL"; then
  EXPECTED="$(grep "$ASSET_NAME" "$TMP_DIR/checksums.txt" | awk '{print $1}')"
  if [ -n "$EXPECTED" ]; then
    ACTUAL="$(sha256sum "$TMP_DIR/$ASSET_NAME" | awk '{print $1}')"
    if [ "$EXPECTED" != "$ACTUAL" ]; then
      log_err "SHA256 mismatch"; exit 1
    fi
    log_ok "SHA256 verified"
  fi
fi

case "$EXT" in
  AppImage)
    INSTALL_DIR="${INSTALL_DIR:-$HOME/.local/bin}"
    mkdir -p "$INSTALL_DIR"
    cp "$TMP_DIR/$ASSET_NAME" "$INSTALL_DIR/gbt-app"
    chmod +x "$INSTALL_DIR/gbt-app"
    log_ok "Installed to $INSTALL_DIR/gbt-app"
    ;;
  dmg)
    log_info "Mounting DMG..."
    MOUNT_POINT="$(hdiutil attach -nobrowse -mountpoint "$TMP_DIR/mount" "$TMP_DIR/$ASSET_NAME" | tail -n 1 | awk '{print $3}')"
    APP_NAME="GBT AI Workstation.app"
    cp -R "$MOUNT_POINT/$APP_NAME" "$HOME/Applications/"
    hdiutil detach "$MOUNT_POINT" >/dev/null
    log_ok "Installed to $HOME/Applications/$APP_NAME"
    ;;
esac
