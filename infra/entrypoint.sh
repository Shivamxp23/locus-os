#!/bin/bash
set -e

# Fix ownership of /vault for obsidian sync
if [ -d "/vault" ]; then
    chown -R 1000:1000 /vault 2>/dev/null || true
fi

# Fix ownership of /var/syncthing for syncthing service
if [ -d "/var/syncthing" ]; then
    chown -R 1000:1000 /var/syncthing 2>/dev/null || true
fi

exec "$@"
