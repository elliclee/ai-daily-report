#!/usr/bin/env python3
"""Schema-ish validation for data/daily.json.

Goal: prevent format drift by ensuring required fields exist and are non-empty.
This is intentionally strict for the push pipeline.

Exit codes:
- 0 OK
- 2 validation failed
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DAILY_PATH = ROOT / "data" / "daily.json"

REQUIRED_SECTIONS = ["releases", "updates", "opensource", "benchmarks", "business", "risks"]

# Optional but recommended: X highlights (8-12 items). When present, validate shape.


def die(msg: str):
    print(f"[validate_json] {msg}", file=sys.stderr)
    raise SystemExit(2)


def must_str(obj, key: str, ctx: str):
    v = obj.get(key)
    if not isinstance(v, str) or not v.strip():
        die(f"{ctx}: missing/empty '{key}'")
    return v


def must_list(obj, key: str, ctx: str):
    v = obj.get(key)
    if not isinstance(v, list):
        die(f"{ctx}: '{key}' must be a list")
    return v


# Legacy field names that AI models sometimes generate instead of the correct ones.
LEGACY_FIELD_HINTS = {
    "source": "use 'sources' (array of {name, url}) instead of 'source'",
    "published": "use 'time' instead of 'published'",
    "summary": "use 'what' + 'why' instead of 'summary'",
    "category": "remove 'category' (section key implies the category)",
}


def validate_item(it: dict, ctx: str):
    if not isinstance(it, dict):
        die(f"{ctx}: item must be object")

    # Detect legacy field names and give actionable hints
    for old_key, hint in LEGACY_FIELD_HINTS.items():
        if old_key in it:
            die(f"{ctx}: found legacy field '{old_key}' — {hint}")

    must_str(it, "title", ctx)
    time_str = must_str(it, "time", ctx)
    must_str(it, "what", ctx)
    must_str(it, "why", ctx)

    # Warn if time is older than 48h (prompt constraint)
    try:
        dt = datetime.strptime(time_str.strip(), "%Y-%m-%d")
        cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
        if dt.replace(tzinfo=timezone.utc) < cutoff:
            print(f"[validate_json] WARNING: {ctx} time '{time_str}' is older than 48h", file=sys.stderr)
    except ValueError:
        pass  # non-standard date format, skip check

    sources = must_list(it, "sources", ctx)
    if len(sources) < 1:
        die(f"{ctx}: sources must have at least 1 entry")

    for i, s in enumerate(sources):
        if not isinstance(s, dict):
            die(f"{ctx}: sources[{i}] must be object")
        must_str(s, "name", f"{ctx}: sources[{i}]")
        must_str(s, "url", f"{ctx}: sources[{i}]")


def main():
    if not DAILY_PATH.exists():
        die(f"missing {DAILY_PATH}")
    daily = json.loads(DAILY_PATH.read_text(encoding="utf-8"))

    must_str(daily, "date", "daily")

    headlines = must_list(daily, "headlines", "daily")
    if not (3 <= len(headlines) <= 5):
        die(f"daily.headlines must be 3-5 items (got {len(headlines)})")
    for idx, it in enumerate(headlines, 1):
        validate_item(it, f"daily.headlines[{idx}]")

    sections = daily.get("sections")
    if not isinstance(sections, dict):
        die("daily.sections must be object")
    for k in REQUIRED_SECTIONS:
        v = sections.get(k)
        if not isinstance(v, list):
            die(f"daily.sections.{k} must be list (can be empty)")
        for idx, it in enumerate(v, 1):
            validate_item(it, f"daily.sections.{k}[{idx}]")

    # Optional X highlights (recommended). When present, validate shape.
    xh = daily.get("x_highlights")
    if xh is not None:
        if not isinstance(xh, list):
            die("daily.x_highlights must be a list when present")
        if not (0 <= len(xh) <= 20):
            die(f"daily.x_highlights size out of range (got {len(xh)})")
        for i, x in enumerate(xh, 1):
            if not isinstance(x, dict):
                die(f"daily.x_highlights[{i}] must be object")
            must_str(x, "author", f"daily.x_highlights[{i}]")
            must_str(x, "handle", f"daily.x_highlights[{i}]")
            must_str(x, "text", f"daily.x_highlights[{i}]")
            must_str(x, "url", f"daily.x_highlights[{i}]")
            for k in ("likes", "reposts", "replies"):
                if k in x and not isinstance(x[k], int):
                    die(f"daily.x_highlights[{i}].{k} must be int")

    # Require: the report should include X as a source somewhere.
    # Either provide x_highlights (preferred) or at least one X link in any sources.
    def has_any_x_link() -> bool:
        for it in (daily.get("headlines") or []):
            for s in (it.get("sources") or []):
                url = str((s or {}).get("url", ""))
                if "x.com/" in url or "twitter.com/" in url:
                    return True
        for sec in (daily.get("sections") or {}).values():
            for it in (sec or []):
                for s in (it.get("sources") or []):
                    url = str((s or {}).get("url", ""))
                    if "x.com/" in url or "twitter.com/" in url:
                        return True
        return False

    if (xh is None or len(xh) == 0) and not has_any_x_link():
        print("[validate_json] WARNING: no X/Twitter source found (x_highlights empty, no x.com links in sources)", file=sys.stderr)

    summary = daily.get("summary")
    if not isinstance(summary, dict):
        die("daily.summary must be object")
    bullets = summary.get("bullets")
    if not isinstance(bullets, list) or not (3 <= len(bullets) <= 5) or any((not isinstance(b, str) or not b.strip()) for b in bullets):
        die("daily.summary.bullets must be 3-5 non-empty strings")
    must_str(summary, "url", "daily.summary")
    must_str(summary, "archiveUrl", "daily.summary")

    print("[validate_json] ok")

    # Validate self_check sub-fields (warnings only, not blocking)
    sc = daily.get("self_check")
    if not isinstance(sc, dict) or not sc:
        print("[validate_json] WARNING: self_check is missing or empty", file=sys.stderr)
    else:
        for required_key in ["coverage_analysis", "freshness_check", "bird_status", "dedupe_keys"]:
            if required_key not in sc:
                print(f"[validate_json] WARNING: self_check.{required_key} is missing", file=sys.stderr)
            elif not sc[required_key]:
                print(f"[validate_json] WARNING: self_check.{required_key} is empty", file=sys.stderr)


if __name__ == "__main__":
    main()
