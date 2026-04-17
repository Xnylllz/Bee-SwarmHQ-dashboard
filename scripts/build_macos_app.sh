#!/bin/zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

python3 -m pip install -r requirements.txt
python3 -m pip install -r requirements-build.txt

rm -rf build dist

python3 -m PyInstaller --clean packaging/BeeHQ.spec

echo
echo "Built app bundle:"
echo "  $ROOT_DIR/dist/BeeHQ.app"
