#!/usr/bin/env bash
# Deploy the AbletonMCP Remote Script from this repo into the Ableton app bundle.
# Ableton loads the control surface from inside the .app, NOT from this repo, so every
# change to AbletonMCP_Remote_Script/__init__.py must be copied over and the stale
# bytecode cleared. Run this, then RESTART Ableton (or reselect the AbletonMCP control
# surface in Preferences -> Link/Tempo/MIDI) for the changes to take effect.
#
# Usage: ./deploy_remote_script.sh
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$REPO_DIR/AbletonMCP_Remote_Script/__init__.py"

if [[ ! -f "$SRC" ]]; then
  echo "ERROR: source not found: $SRC" >&2
  exit 1
fi

# Find installed AbletonMCP control-surface folders inside any Ableton Live app bundle.
mapfile -t DESTS < <(find /Applications -type d -path "*/MIDI Remote Scripts/AbletonMCP" 2>/dev/null)

if [[ ${#DESTS[@]} -eq 0 ]]; then
  echo "ERROR: no installed AbletonMCP folder found under /Applications/Ableton*.app" >&2
  echo "Is the Remote Script installed? Expected: <App>/Contents/App-Resources/MIDI Remote Scripts/AbletonMCP" >&2
  exit 1
fi

for DST in "${DESTS[@]}"; do
  echo "Deploying to: $DST"
  cp "$SRC" "$DST/__init__.py"
  rm -rf "$DST/__pycache__"
  echo "  copied __init__.py ($(wc -l < "$SRC") lines) + cleared bytecode"
done

echo
echo "Done. Now RESTART Ableton (or reselect the AbletonMCP control surface) to load the changes."
