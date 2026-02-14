#!/usr/bin/env python3
"""Renderer aligned to 2026-02-13 report style (card layout + self-check + X highlights).

Contract:
- Reads JSON data from:
    data/daily.json
    data/techneme.json   (optional; can be missing)
- Renders ONE full HTML page into:
    archive/YYYY-MM-DD.html
- Makes homepage equal to the full daily page:
    index.html == archive/YYYY-MM-DD.html

This script intentionally contains NO web fetches and NO model/tool calls.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
ARCHIVE_DIR = ROOT / "archive"
TEMPLATE_PATH = ROOT / "template.html"


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def html_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def render_sources(sources: list[dict]) -> str:
    if not sources:
        return ""
    links = []
    for src in sources:
        name = html_escape(str(src.get("name", "source")))
        url = html_escape(str(src.get("url", "")))
        if url:
            links.append(f'<a href="{url}" target="_blank">{name}</a>')
        else:
            links.append(name)
    return "、".join(links)


def render_cards(items: list[dict], badge_color: str | None = None, tag: str | None = None) -> str:
    parts: list[str] = []
    for it in items or []:
        title = html_escape(str(it.get("title", "")))
        when = html_escape(str(it.get("time", "")))
        what = html_escape(str(it.get("what", "")))
        why = html_escape(str(it.get("why", "")))
        sources_html = render_sources(it.get("sources", []) or [])

        color_style = f' style="background: {badge_color};"' if badge_color else ""

        parts.append('<div class="card">')
        parts.append('<div class="card-headline">')
        parts.append(f'<div class="card-badge"{color_style}></div>')
        parts.append(f'<h3 class="card-title">{title}</h3>')
        parts.append('</div>')

        meta = []
        if tag:
            meta.append(f'<span class="tag">{html_escape(tag)}</span>')
        if when:
            meta.append(f'<span>📅 {when}</span>')
        if meta:
            parts.append('<div class="card-meta">' + "\n".join(meta) + '</div>')

        parts.append('<div class="card-content">')
        if why:
            parts.append(f'<strong>为什么重要：</strong>{why}')
        if what:
            parts.append(f'<div style="margin-top: 10px;"><strong>事件：</strong>{what}</div>')
        parts.append('</div>')

        if sources_html:
            parts.append('<div class="card-sources">')
            parts.append(f'来源：{sources_html}')
            parts.append('</div>')

        parts.append('</div>')

    return "\n".join(parts)


def render_x_highlights(items: list[dict] | None) -> str:
    items = items or []
    parts: list[str] = []
    parts.append('<!-- X 高互动事件 -->')
    parts.append('<div class="x-highlight">')
    parts.append('<h4>🔥 X 高互动事件（8-12条）</h4>')

    if not items:
        parts.append('<div class="x-item"><div class="x-avatar">?</div><div class="x-content"><div class="x-text">今日无（或 bird 未配置/抓取失败）。</div></div></div>')
        parts.append('</div>')
        return "\n".join(parts)

    for x in items[:12]:
        author = html_escape(str(x.get("author", "")))
        handle = html_escape(str(x.get("handle", "")))
        text = html_escape(str(x.get("text", "")))
        url = html_escape(str(x.get("url", "")))
        likes = x.get("likes")
        reposts = x.get("reposts")
        replies = x.get("replies")
        eng = []
        if isinstance(likes, int):
            eng.append(f"❤️ {likes}")
        if isinstance(reposts, int):
            eng.append(f"🔄 {reposts}")
        if isinstance(replies, int):
            eng.append(f"💬 {replies}")
        eng_html = " | ".join(eng)

        parts.append('<div class="x-item">')
        parts.append('<div class="x-avatar">🧵</div>')
        parts.append('<div class="x-content">')
        parts.append(f'<div class="x-author">{author} <span class="x-handle">{handle}</span></div>')
        parts.append(f'<div class="x-text">{text}</div>')
        if eng_html:
            parts.append(f'<div class="x-engagement">{eng_html}</div>')
        if url:
            parts.append(f'<div style="margin-top:6px;"><a href="{url}" target="_blank" style="color: var(--accent); text-decoration:none; font-size:12px;">查看原贴 →</a></div>')
        parts.append('</div>')
        parts.append('</div>')

    parts.append('</div>')
    return "\n".join(parts)


def render_self_check(daily: dict) -> str:
    sections = daily.get("sections") or {}

    # counts
    releases = len(sections.get("releases") or [])
    updates = len(sections.get("updates") or [])
    opensource = len(sections.get("opensource") or [])
    benchmarks = len(sections.get("benchmarks") or [])
    business = len(sections.get("business") or [])
    risks = len(sections.get("risks") or [])

    parts: list[str] = []
    parts.append('<!-- 覆盖度自检 -->')
    parts.append('<section class="section">')
    parts.append('<h2 class="section-title"><span>📊</span> 覆盖度自检</h2>')

    parts.append('<div class="highlight-box">')
    parts.append('<div class="highlight-title">栏目统计</div>')
    parts.append('<ul class="highlight-list">')
    parts.append(f'<li><span>🚀</span><div>Releases: {releases}条</div></li>')
    parts.append(f'<li><span>📈</span><div>Updates: {updates}条</div></li>')
    parts.append(f'<li><span>🔓</span><div>OpenSource: {opensource}条</div></li>')
    parts.append(f'<li><span>📊</span><div>Benchmarks: {benchmarks}条</div></li>')
    parts.append(f'<li><span>💼</span><div>Business: {business}条</div></li>')
    parts.append(f'<li><span>⚠️</span><div>Risks: {risks}条</div></li>')
    parts.append('</ul>')
    parts.append('</div>')

    vendors = daily.get("vendorsHit") or []
    if vendors:
        parts.append('<div class="highlight-box">')
        parts.append('<div class="highlight-title">命中厂商清单</div>')
        parts.append('<p style="font-size: 13px; line-height: 1.8; margin-top: 8px;">')
        parts.append(" ".join([f'<span class="tag">✅ {html_escape(v)}</span>' for v in vendors]))
        parts.append('</p>')
        parts.append('</div>')

    dedup = daily.get("dedupKeys") or []
    if dedup:
        parts.append('<div class="highlight-box">')
        parts.append('<div class="highlight-title">Deduplicate Keys</div>')
        parts.append('<p style="font-size: 12px; line-height: 1.6; margin-top: 8px; color: var(--muted-foreground);">')
        parts.append(html_escape(" | ".join(dedup)))
        parts.append('</p>')
        parts.append('</div>')

    parts.append('</section>')
    return "\n".join(parts)


def main():
    daily = load_json(DATA_DIR / "daily.json", default={})
    date = str(daily.get("date") or datetime.utcnow().strftime("%Y-%m-%d"))

    # date parts for header
    try:
        dt = datetime.strptime(date, "%Y-%m-%d")
    except Exception:
        dt = datetime.utcnow()
    date_day = str(dt.day)
    date_month = dt.strftime("%B %Y")
    date_human = dt.strftime("%B %d, %Y")

    tpl = TEMPLATE_PATH.read_text(encoding="utf-8")

    sections = daily.get("sections") or {}

    # Map to 2026-02-13 style sections
    content_parts: list[str] = []

    # Core
    content_parts.append('<!-- 核心看点 -->')
    content_parts.append('<section class="section">')
    content_parts.append('<h2 class="section-title"><span>🔥</span> 核心看点</h2>')
    content_parts.append(render_cards(daily.get("headlines") or []))
    content_parts.append('</section>')

    # New models/tools = releases+updates+opensource+benchmarks
    new_models = (sections.get("releases") or []) + (sections.get("updates") or []) + (sections.get("opensource") or []) + (sections.get("benchmarks") or [])
    content_parts.append('<!-- 新模型/工具 -->')
    content_parts.append('<section class="section">')
    content_parts.append('<h2 class="section-title"><span>🚀</span> 新模型/工具</h2>')
    content_parts.append(render_cards(new_models))
    content_parts.append('</section>')

    # Business
    content_parts.append('<!-- 企业动态 -->')
    content_parts.append('<section class="section">')
    content_parts.append('<h2 class="section-title"><span>💼</span> 企业动态</h2>')
    content_parts.append(render_cards(sections.get("business") or []))
    content_parts.append('</section>')

    # Risks
    content_parts.append('<!-- 风险/事故 -->')
    content_parts.append('<section class="section">')
    content_parts.append('<h2 class="section-title"><span>⚠️</span> 风险/事故</h2>')
    content_parts.append(render_cards(sections.get("risks") or []))
    content_parts.append('</section>')

    # X highlights placed after new models/tools, like 2/13
    # If you want it inside 新模型/工具 section, the generator can place it in x_highlights and render_x_highlights here.
    # We'll append an extra block right after 新模型/工具 section by rendering it here.
    # (This is a separate block but matches the 2/13 placement conceptually.)
    content_parts.insert(9, render_x_highlights(daily.get("x_highlights")))

    # Self-check
    content_parts.append(render_self_check(daily))

    content_html = "\n".join([p for p in content_parts if p and p.strip()])

    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    out = tpl
    out = out.replace("{{DATE_HUMAN}}", html_escape(date_human))
    out = out.replace("{{DATE_DAY}}", html_escape(date_day))
    out = out.replace("{{DATE_MONTH}}", html_escape(date_month))
    out = out.replace("{{CONTENT}}", content_html)
    out = out.replace("{{GENERATED_AT_UTC}}", html_escape(now_utc))

    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    archive_path = ARCHIVE_DIR / f"{date}.html"
    archive_path.write_text(out, encoding="utf-8")

    shutil.copyfile(archive_path, ROOT / "index.html")

    print(str(archive_path))


if __name__ == "__main__":
    main()
