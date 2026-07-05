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
# (portable: works on macOS's bash 3.2 — no mapfile)
found=0
line_count=$(wc -l < "$SRC" | tr -d ' ')

# First, collect all destinations to show summary
declare -a dests
while IFS= read -r DST; do
  [[ -z "$DST" ]] && continue
  dests+=("$DST")
done < <(find /Applications -type d -path "*/MIDI Remote Scripts/AbletonMCP" 2>/dev/null | sort)

if [[ ${#dests[@]} -eq 0 ]]; then
  echo "ERROR: no installed AbletonMCP folder found under /Applications/Ableton*.app" >&2
  echo "Is the Remote Script installed? Expected: <App>/Contents/App-Resources/MIDI Remote Scripts/AbletonMCP" >&2
  exit 1
fi

# Show which Ableton instances will be updated
echo "Found ${#dests[@]} Ableton installation(s):"
for dst in "${dests[@]}"; do
  app_path=$(echo "$dst" | sed 's|/Contents/App-Resources.*||')
  app_name=$(basename "$app_path")
  echo "  • $app_name"
done
echo

# Deploy to each one
for DST in "${dests[@]}"; do
  app_path=$(echo "$DST" | sed 's|/Contents/App-Resources.*||')
  app_name=$(basename "$app_path")
  echo "Deploying to: $app_name"
  cp "$SRC" "$DST/__init__.py"
  rm -rf "$DST/__pycache__"
  echo "  ✓ copied __init__.py ($line_count lines) + cleared bytecode"
done

echo
echo "Done. Now RESTART each Ableton instance (or reselect the AbletonMCP control surface in Preferences → Link/Tempo/MIDI) to load the changes."
