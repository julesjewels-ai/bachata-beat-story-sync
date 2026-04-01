#!/usr/bin/env bash
# build_production.sh
# Creates a minimal, production-ready bundle of the Bachata Beat-Story Sync tool.

set -e

DIST_DIR="dist"
ARCHIVE_NAME="bachata-sync-prod.tar.gz"

echo "🧹 Cleaning previous builds..."
rm -rf "$DIST_DIR"
mkdir -p "$DIST_DIR/bachata-sync-prod"

echo "📦 Packaging required production files..."

# Copy only the strictly necessary files into our staging directory
cp -r src "$DIST_DIR/bachata-sync-prod/"
cp main.py "$DIST_DIR/bachata-sync-prod/"
cp montage_config.yaml "$DIST_DIR/bachata-sync-prod/"
cp requirements.txt "$DIST_DIR/bachata-sync-prod/"

# Include package definition files if they exist
cp pyproject.toml "$DIST_DIR/bachata-sync-prod/" 2>/dev/null || true
cp requirements.in "$DIST_DIR/bachata-sync-prod/" 2>/dev/null || true
cp .env.example "$DIST_DIR/bachata-sync-prod/" 2>/dev/null || true

# Strip any python cache files that accidentally crept in
find "$DIST_DIR/bachata-sync-prod" -type d -name "__pycache__" -exec rm -rf {} +
find "$DIST_DIR/bachata-sync-prod" -type f -name "*.pyc" -delete

echo "🗜️ Creating archive..."
cd "$DIST_DIR"
tar -czf "$ARCHIVE_NAME" bachata-sync-prod
cd ..

echo "✅ Done!"
echo "Your production-ready code is available in: $DIST_DIR/bachata-sync-prod/"
echo "A compressed archive is ready to deploy at: $DIST_DIR/$ARCHIVE_NAME"
