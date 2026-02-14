#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

DATE_UTC="${1:-$(date -u +%F)}"
ARCHIVE="archive/${DATE_UTC}.html"

if [[ ! -f "$ARCHIVE" ]]; then
  echo "[verify] missing archive: $ARCHIVE" >&2
  exit 2
fi

if [[ ! -f index.html ]]; then
  echo "[verify] missing index.html" >&2
  exit 3
fi

# Validate JSON schema-ish constraints to prevent format drift
python3 scripts/validate_json.py

ARCHIVE_SHA=$(sha256sum "$ARCHIVE" | awk '{print $1}')
INDEX_SHA=$(sha256sum index.html | awk '{print $1}')

if [[ "$ARCHIVE_SHA" != "$INDEX_SHA" ]]; then
  echo "[verify] index.html is NOT identical to $ARCHIVE" >&2
  echo "[verify] archive_sha=$ARCHIVE_SHA" >&2
  echo "[verify] index_sha=$INDEX_SHA" >&2
  exit 4
fi

echo "[verify] ok: index.html == $ARCHIVE"
