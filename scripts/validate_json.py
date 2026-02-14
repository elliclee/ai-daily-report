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
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DAILY_PATH = ROOT / "data" / "daily.json"

REQUIRED_SECTIONS = ["releases", "updates", "opensource", "benchmarks", "business", "risks"]


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


def validate_item(it: dict, ctx: str):
    if not isinstance(it, dict):
        die(f"{ctx}: item must be object")
    must_str(it, "title", ctx)
    must_str(it, "time", ctx)
    must_str(it, "what", ctx)
    must_str(it, "why", ctx)
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
    if len(headlines) != 5:
        die(f"daily.headlines must be exactly 5 items (got {len(headlines)})")
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

    summary = daily.get("summary")
    if not isinstance(summary, dict):
        die("daily.summary must be object")
    bullets = summary.get("bullets")
    if not isinstance(bullets, list) or len(bullets) != 5 or any((not isinstance(b, str) or not b.strip()) for b in bullets):
        die("daily.summary.bullets must be exactly 5 non-empty strings")
    must_str(summary, "url", "daily.summary")
    must_str(summary, "archiveUrl", "daily.summary")

    print("[validate_json] ok")


if __name__ == "__main__":
    main()
