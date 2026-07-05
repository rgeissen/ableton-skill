#!/usr/bin/env bash
# Build the Claude Desktop skill pack from .claude/skills/*.
# Each skill becomes its own zip (<name>/SKILL.md at the root), with the non-standard
# `compatibility:` frontmatter line stripped so it validates on upload.
# Output: dist/claude-desktop/<name>.zip  (+ INSTALL.md, + convenience bundle)
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$REPO_DIR/.claude/skills"
OUT="$REPO_DIR/skill-pack"

# Preserve a hand-written INSTALL.md if present.
INSTALL_BAK=""
if [[ -f "$OUT/INSTALL.md" ]]; then
  INSTALL_BAK="$(mktemp)"; cp "$OUT/INSTALL.md" "$INSTALL_BAK"
fi

rm -rf "$OUT"; mkdir -p "$OUT"
[[ -n "$INSTALL_BAK" ]] && cp "$INSTALL_BAK" "$OUT/INSTALL.md"

for f in "$SRC_DIR"/*/SKILL.md; do
  name="$(sed -n 's/^name:[[:space:]]*//p' "$f" | head -1)"
  [[ -z "$name" ]] && { echo "WARN: no name in $f, skipping" >&2; continue; }
  mkdir -p "$OUT/$name"
  grep -v '^compatibility:' "$f" > "$OUT/$name/SKILL.md"
  ( cd "$OUT" && zip -qr "${name}.zip" "$name" )
  echo "built ${name}.zip"
done

( cd "$OUT" && zip -qr "ableton-skill-pack-all.zip" ./*.zip )
echo "built ableton-skill-pack-all.zip (convenience bundle)"

# Remove the intermediate unzipped skill folders — keep only the .zip files + INSTALL.md.
for d in "$OUT"/*/; do
  [[ -d "$d" && -f "${d}SKILL.md" ]] && rm -rf "$d"
done
echo "Output: $OUT (zips + INSTALL.md)"
