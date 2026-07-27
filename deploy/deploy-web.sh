#!/bin/bash
set -e

SOURCE="/opt/dataark/app/static"
TARGET="/var/www/html"

echo
echo "Deploying website..."
echo "  From: $SOURCE"
echo "    To: $TARGET"

sudo mkdir -p "$TARGET"

sudo rsync -av --delete \
    --exclude='*.bak' \
    "$SOURCE"/ \
    "$TARGET"/

echo
echo "Deployment complete."

echo
echo "Current website:"
find "$TARGET" -maxdepth 2 | sort
