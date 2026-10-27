#!/usr/bin/env bash
# Verify a Marp study/presentation deck directory is internally consistent.
#
#   verify-deck.sh <deck-dir>
#
# Artifact prefix is auto-detected from the directory name:
#   study/<topic>/chXX-<slug>/  -> chXX-slides.{html,pdf,pptx}, chXX-script.md
#   presentation/<topic>/       -> slides.{html,pdf,pptx}, script.md
set -euo pipefail
DIR="${1:-.}"
cd "$DIR"

fail=0
note() { echo "  $*"; }
bad()  { echo "FAIL: $*"; fail=1; }

[[ -f slides.md ]] || { echo "no slides.md in $DIR"; exit 1; }

# AGENTS.md: chapter folders must prefix their build outputs with chXX-.
base=$(basename "$PWD")
if [[ $base =~ ^(ch[0-9]+)- ]]; then
  PFX="${BASH_REMATCH[1]}-"
else
  PFX=""
fi
note "artifact prefix: '${PFX}'"

# Slides are separated by '---'. The front-matter contributes one extra
# separator (its opening line is NR==1, its closing line counts), so:
#   slides = (# of '---' lines) - 1
slides=$(awk '/^---[[:space:]]*$/ {c++} END {print c-1}' slides.md)
note "slides.md slide count: $slides"

HTML="${PFX}slides.html"; PDF="${PFX}slides.pdf"
PPTX="${PFX}slides.pptx"; SCRIPT="${PFX}script.md"

for f in "$HTML" "$PDF" "$PPTX" "$SCRIPT" README.md; do
  [[ -f $f ]] || bad "missing $f"
done

for f in "$HTML" "$PDF" "$PPTX"; do
  [[ -f $f ]] || continue
  [[ $f -nt slides.md ]] || bad "$f is older than slides.md (rebuild needed)"
done

if [[ -f $PPTX ]]; then
  # Exclude notesSlideN.xml.rels, which would double the count.
  notes=$(unzip -l "$PPTX" 2>/dev/null | awk '/notesSlide[0-9]+\.xml$/ {c++} END {print c+0}')
  note "pptx notesSlide count: $notes"
  [[ "$notes" == "$slides" ]] || bad "pptx notes ($notes) != slides ($slides)"
fi

if [[ -f $SCRIPT ]]; then
  sections=$(awk '/^## / {c++} END {print c+0}' "$SCRIPT")
  note "$SCRIPT section count: $sections"
  [[ "$sections" == "$slides" ]] || bad "script sections ($sections) != slides ($slides)"
fi

# Chromium renders U+2194 as an emoji glyph in Marp HTML/PDF.
if grep -q '↔' slides.md; then
  bad "slides.md contains '↔' — replace with '→' or plain words"
fi

[[ $fail -eq 0 ]] && echo "OK: deck consistent ($slides slides)"
exit $fail
