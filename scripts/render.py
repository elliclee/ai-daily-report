#!/usr/bin/env python3
"""Deterministic renderer for AI Daily Report.

Contract:
- Reads JSON data from:
    data/daily.json
    data/techneme.json   (optional; can be missing)
- Renders ONE full HTML page into:
    archive/YYYY-MM-DD.html
- Makes homepage equal to the full daily page:
    index.html == archive/YYYY-MM-DD.html (byte-identical via copy)

This script intentionally contains NO web fetches and NO model/tool calls.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime
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
        name = html_escape(src.get("name", "source"))
        url = html_escape(src.get("url", ""))
        if url:
            links.append(f'<a href="{url}" target="_blank">{name}</a>')
        else:
            links.append(name)
    return "、".join(links)


def render_items(items: list[dict]) -> str:
    # Simple, stable markup. Style is handled by template.html
    parts = []
    for it in items:
        title = html_escape(it.get("title", ""))
        when = html_escape(it.get("time", ""))
        what = html_escape(it.get("what", ""))
        why = html_escape(it.get("why", ""))
        sources_html = render_sources(it.get("sources", []) or [])
        parts.append(
            "\n".join(
                [
                    '<article class="news-item">',
                    f'  <h3 class="news-title">{title}</h3>' if title else "",
                    f'  <div class="news-meta">{when}</div>' if when else "",
                    f'  <div class="news-desc"><strong>事件：</strong>{what}</div>' if what else "",
                    f'  <div class="news-desc"><strong>为什么重要：</strong>{why}</div>' if why else "",
                    f'  <div class="card-sources">来源：{sources_html}</div>' if sources_html else "",
                    "</article>",
                ]
            )
        )
    return "\n".join([p for p in parts if p.strip()])


def render_x_highlights(items: list[dict] | None) -> str:
    # Always render to keep layout stable.
    parts = [
        '<section class="section">',
        '  <h2 class="section-title">🔥 X 高互动事件（8-12条）</h2>',
    ]

    items = items or []
    if not items:
        parts.append('<div class="news-desc">今日无（或 bird 未配置/抓取失败）。</div>')
        parts.append('</section>')
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

        parts.append('<article class="news-item">')
        parts.append(f'  <h3 class="news-title">{author} <span style="color: var(--text-secondary); font-weight: 400;">{handle}</span></h3>')
        parts.append(f'  <div class="news-desc">{text}</div>')
        if eng_html:
            parts.append(f'  <div class="news-meta">{eng_html}</div>')
        if url:
            parts.append(f'  <a class="news-link" href="{url}" target="_blank">查看原贴 →</a>')
        parts.append('</article>')

    parts.append('</section>')
    return "\n".join(parts)


def render_techneme(stories: list[dict]) -> str:
    # Always render this section to keep page layout stable.
    parts = [
        '<section class="section">',
        '  <h2 class="section-title">🌐 TechMeme 当日头条</h2>',
    ]

    if not stories:
        parts.append('<div class="news-desc">今日无（或抓取失败）。</div>')
        parts.append('</section>')
        return "\n".join(parts)

    for s in stories[:5]:
        title = html_escape(s.get("title", ""))
        url = html_escape(s.get("url", ""))
        summary = html_escape(s.get("summary", ""))
        parts.append('<article class="news-item">')
        parts.append(f'  <h3 class="news-title">{title}</h3>')
        if summary:
            parts.append(f'  <div class="news-desc">{summary}</div>')
        if url:
            parts.append(f'  <a class="news-link" href="{url}" target="_blank">阅读更多 →</a>')
        parts.append('</article>')
    parts.append('</section>')
    return "\n".join(parts)


def main():
    daily = load_json(DATA_DIR / "daily.json", default={})
    techneme = load_json(DATA_DIR / "techneme.json", default={"stories": []})

    date = daily.get("date") or datetime.utcnow().strftime("%Y-%m-%d")

    tpl = TEMPLATE_PATH.read_text(encoding="utf-8")

    # template.html placeholders we currently support:
    # - {{DATE}}     (YYYY-MM-DD)
    # - {{DATE_CN}}  (YYYY年M月D日)
    # - {{CONTENT}}  (full daily report HTML)
    # - {{ARCHIVE_LINKS}} (simple archive list)

    sections = daily.get("sections") or {}

    # Build content blocks in a fixed order.
    content_parts = []
    content_parts.append('<section class="section">')
    content_parts.append('  <h2 class="section-title">🔥 核心看点</h2>')
    content_parts.append(render_items(daily.get("headlines") or []))
    content_parts.append('</section>')

    # X highlights (layout-stable)
    content_parts.append(render_x_highlights(daily.get("x_highlights")))

    # Keep section layout stable: always show TechMeme section (with placeholder when empty).
    content_parts.append(render_techneme((techneme or {}).get("stories") or []))

    def add_section(title: str, items: list[dict]):
        content_parts.append('<section class="section">')
        content_parts.append(f'  <h2 class="section-title">{html_escape(title)}</h2>')
        content_parts.append(render_items(items or []))
        content_parts.append('</section>')

    add_section('🚀 发布 / 上线', sections.get('releases') or [])
    add_section('📈 更新 / 迭代', sections.get('updates') or [])
    add_section('🔓 开源 / 权重', sections.get('opensource') or [])
    add_section('📊 评测 / 基准', sections.get('benchmarks') or [])
    add_section('💼 商业 / 融资', sections.get('business') or [])
    add_section('⚠️ 风险 / 事故', sections.get('risks') or [])

    content_html = "\n".join([p for p in content_parts if p and p.strip()])

    # Archive links (latest 14 days if present)
    archive_links = []
    for p in sorted(ARCHIVE_DIR.glob('*.html'), reverse=True)[:14]:
        name = p.stem
        archive_links.append(f'<a href="./archive/{name}.html">{name}</a>')
    archive_links_html = "\n".join(archive_links)

    # Date CN
    try:
        dt = datetime.strptime(date, "%Y-%m-%d")
        date_cn = f"{dt.year}年{dt.month}月{dt.day}日"
    except Exception:
        date_cn = date

    out = tpl
    out = out.replace("{{DATE}}", html_escape(date))
    out = out.replace("{{DATE_CN}}", html_escape(date_cn))
    out = out.replace("{{CONTENT}}", content_html)
    out = out.replace("{{ARCHIVE_LINKS}}", archive_links_html)

    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    archive_path = ARCHIVE_DIR / f"{date}.html"
    archive_path.write_text(out, encoding="utf-8")

    # Homepage = full daily report
    shutil.copyfile(archive_path, ROOT / "index.html")

    print(str(archive_path))


if __name__ == "__main__":
    main()
