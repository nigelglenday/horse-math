#!/usr/bin/env bash
# Stage repo content into _site_src/ for MkDocs.
# Preserves the original directory structure so internal markdown links
# keep resolving without rewriting.
#
# Usage: ./scripts/build_docs.sh
# Then: mkdocs build (or mkdocs serve for local preview)

set -euo pipefail

SRC="_site_src"

rm -rf "$SRC"
mkdir -p "$SRC"

# Top-level docs
cp README.md "$SRC/"
cp CLAUDE.md "$SRC/"
cp LICENSE "$SRC/LICENSE.md"   # mkdocs renders .md but link in README is "LICENSE"

# Architecture
mkdir -p "$SRC/docs"
cp docs/ARCHITECTURE.md "$SRC/docs/"

# Case studies (markdown)
mkdir -p "$SRC/analysis/case-studies/2026-kentucky-derby"
cp analysis/case-studies/2026-kentucky-derby/*.md \
   "$SRC/analysis/case-studies/2026-kentucky-derby/"

# Figures (preserve relative paths so embedded images resolve)
mkdir -p "$SRC/analysis/figures/2026-kentucky-derby"
cp analysis/figures/2026-kentucky-derby/*.png \
   "$SRC/analysis/figures/2026-kentucky-derby/"

# Learnings
mkdir -p "$SRC/learnings"
cp learnings/*.md "$SRC/learnings/"

# Optional: seed prompt
mkdir -p "$SRC/prompts"
cp prompts/*.md "$SRC/prompts/"

# Rewrite links to source/data files so they point at GitHub on the live site
# (math.horse can't host the .py and .csv directly).
GH="https://github.com/nigelglenday/horse-math/blob/main"
find "$SRC" -name '*.md' -print0 | while IFS= read -r -d '' f; do
  # Source code files
  sed -i.bak -E "s|\]\((\.\.\/)+(src/[a-z_]+\.py)\)|](${GH}/\2)|g" "$f"
  sed -i.bak -E "s|\]\((src/[a-z_]+\.py)\)|](${GH}/\1)|g" "$f"
  # Data CSV/TOML/TXT files
  sed -i.bak -E "s|\]\((\.\.\/)+(data/races/[^)]+)\)|](${GH}/\2)|g" "$f"
  # pyproject.toml
  sed -i.bak -E "s|\]\(pyproject\.toml\)|](${GH}/pyproject.toml)|g" "$f"
  rm -f "${f}.bak"
done

echo "Staged $(find $SRC -name '*.md' | wc -l | tr -d ' ') markdown files into $SRC/"
