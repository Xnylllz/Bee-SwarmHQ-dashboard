#!/bin/zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

APP_PATH="$ROOT_DIR/dist/BeeHQ.app"
DMG_ROOT="$ROOT_DIR/dist/dmg-root"
DMG_PATH="$ROOT_DIR/dist/BeeHQ-macOS.dmg"

if [ ! -d "$APP_PATH" ]; then
  echo "BeeHQ.app not found. Build the app first with scripts/build_macos_app.sh"
  exit 1
fi

rm -rf "$DMG_ROOT" "$DMG_PATH"
mkdir -p "$DMG_ROOT"
cp -R "$APP_PATH" "$DMG_ROOT/"
ln -s /Applications "$DMG_ROOT/Applications"

hdiutil create -volname "BeeHQ" -srcfolder "$DMG_ROOT" -ov -format UDZO "$DMG_PATH"

echo
echo "Built DMG:"
echo "  $DMG_PATH"
