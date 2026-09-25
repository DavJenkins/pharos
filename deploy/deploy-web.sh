#!/bin/bash
set -e

SOURCE="/opt/dataark/app/static"
TARGET="/var/www/html"

# Fail before changing the deployed site if configuration/artwork is invalid.
cd /opt/dataark
bash tools/render_dashboard.sh

echo
echo "============================================================"
echo " Deploying Data Ark Web Interface"
echo "============================================================"

echo
echo "1. Deploying static website..."

sudo mkdir -p "$TARGET"

sudo rsync -av --delete \
    --exclude='*.bak' \
    --exclude='docs/' \
    "$SOURCE"/ \
    "$TARGET"/

echo
echo "2. Publishing documentation..."

python3 tools/publish_docs.py

echo
echo "3. Installing documentation..."

sudo mkdir -p "$TARGET/docs"

sudo rsync -av --delete \
    /tmp/dataark-docs/ \
    "$TARGET/docs/"

echo
echo "4. Cleaning obsolete files..."

sudo find "$TARGET" \
    -maxdepth 1 \
    -name "index.html.*.bak" \
    -delete

sudo rm -f \
    "$TARGET/index.nginx-debian.html" \
    "$TARGET/status.json" \
    "$TARGET/logs.php"

echo
echo "============================================================"
echo " Deployment Complete"
echo "============================================================"

echo
echo "Website:"
echo "    http://dataark/"

echo
echo "Documentation:"
echo "    http://dataark/docs/"

echo
echo "Swagger:"
echo "    http://dataark/api/docs"
