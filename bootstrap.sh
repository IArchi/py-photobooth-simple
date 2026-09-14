#!/bin/bash

set -euo pipefail

REPO_URL="${PHOTOBOOTH_REPO_URL:-https://github.com/IArchi/py-photobooth-simple.git}"
INSTALL_DIR="${PHOTOBOOTH_INSTALL_DIR:-$HOME/py-photobooth-simple}"

if ! command -v git >/dev/null 2>&1; then
    printf 'Git is required. Install it with: sudo apt-get install -y git\n' >&2
    exit 1
fi

if [ -e "$INSTALL_DIR" ]; then
    printf 'Installation directory already exists: %s\n' "$INSTALL_DIR" >&2
    exit 1
fi

git clone --depth 1 "$REPO_URL" "$INSTALL_DIR"

if [ ! -r /dev/tty ]; then
    printf 'An interactive terminal is required by install.sh.\n' >&2
    exit 1
fi

exec bash "$INSTALL_DIR/install.sh" </dev/tty
