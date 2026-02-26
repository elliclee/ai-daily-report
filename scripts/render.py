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
import re

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
            # Add freshness indicator
            freshness = get_freshness_indicator(when)
            meta.append(f'<span>{freshness} {when}</span>')
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


def get_freshness_indicator(time_str: str) -> str:
    """Return emoji indicator for news freshness."""
    try:
        dt = datetime.strptime(time_str.strip(), "%Y-%m-%d")
        today = datetime.now()
        delta = (today - dt).days
        
        if delta == 0:
            return "🔴"  # Today
        elif delta == 1:
            return "🟡"  # Yesterday
        else:
            return "🟢"  # Within 48h
    except:
        return "📅"


def render_x_highlights(items: list[dict] | None) -> str:
    items = items or []
    parts: list[str] = []
    parts.append('<!-- X 高互动事件 -->')
    parts.append('<div class="x-highlight">')
    parts.append('<h4>🔥 X 高互动事件（8-12条）</h4>')

    if not items:
        parts.append('<div class="x-item"><div class="x-content"><div class="x-text">今日无（或 bird 未配置/抓取失败）。</div></div></div>')
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


def render_self_check_collapsed(daily: dict) -> str:
    """Render self-check section as collapsible details."""
    sections = daily.get("sections") or {}
    sc = daily.get("self_check") or {}

    # counts
    releases = len(sections.get("releases") or [])
    updates = len(sections.get("updates") or [])
    opensource = len(sections.get("opensource") or [])
    benchmarks = len(sections.get("benchmarks") or [])
    business = len(sections.get("business") or [])
    risks = len(sections.get("risks") or [])
    total = releases + updates + opensource + benchmarks + business + risks

    parts: list[str] = []
    parts.append('<details class="self-check-details" style="margin-top: 40px; padding: 16px; background: var(--card); border-radius: 8px;">')
    parts.append('<summary style="cursor: pointer; font-weight: 500; color: var(--muted-foreground);">📊 数据覆盖详情（点击展开）</summary>')
    
    parts.append('<div style="margin-top: 16px;">')
    
    # Section counts with progress bars
    parts.append('<div style="margin-bottom: 16px;">')
    parts.append('<div style="font-size: 12px; color: var(--muted-foreground); margin-bottom: 8px;">栏目统计</div>')
    
    section_data = [
        ("🚀 Releases", releases, "#e85d04"),
        ("📈 Updates", updates, "#4285f4"),
        ("🔓 OpenSource", opensource, "#10a37f"),
        ("📊 Benchmarks", benchmarks, "#8e44ad"),
        ("💼 Business", business, "#7c3aed"),
        ("⚠️ Risks", risks, "#991b1b"),
    ]
    
    for label, count, color in section_data:
        bar_width = min(count * 20, 100)  # Simple visual indicator
        parts.append(f'<div style="display: flex; align-items: center; margin-bottom: 6px; font-size: 12px;">')
        parts.append(f'<span style="width: 100px;">{label}</span>')
        parts.append(f'<div style="flex: 1; height: 6px; background: var(--border); border-radius: 3px; margin: 0 8px;">')
        if count > 0:
            parts.append(f'<div style="width: {bar_width}%; height: 100%; background: {color}; border-radius: 3px;"></div>')
        parts.append('</div>')
        parts.append(f'<span style="width: 30px; text-align: right;">{count}</span>')
        parts.append('</div>')
    
    parts.append('</div>')

    # Coverage analysis
    ca = sc.get("coverage_analysis") or {}
    hit_vendors = ca.get("hit_vendors") or daily.get("vendorsHit") or []
    if hit_vendors:
        parts.append('<div style="margin-top: 12px; font-size: 12px;">')
        parts.append('<div style="color: var(--muted-foreground); margin-bottom: 4px;">命中厂商</div>')
        parts.append(" ".join([f'<span style="display: inline-block; padding: 2px 6px; background: var(--accent-soft); border-radius: 4px; margin: 2px;">✅ {html_escape(str(v))}</span>' for v in hit_vendors]))
        parts.append('</div>')

    # Bird status
    bs = sc.get("bird_status") or {}
    if bs:
        available = bs.get("available", False)
        parts.append('<div style="margin-top: 12px; font-size: 12px;">')
        parts.append(f'<span style="color: var(--muted-foreground);">🐦 Bird 状态：</span>')
        parts.append(f'{"✅ 可用" if available else "❌ 不可用"}')
        if not available and bs.get("fallback"):
            parts.append(f' <span style="color: var(--muted-foreground);">({html_escape(bs["fallback"])})</span>')
        parts.append('</div>')

    parts.append('</div>')
    parts.append('</details>')
    
    return "\n".join(parts)


def render_archive_nav(current_date: str) -> str:
    """Scan archive/ directory and generate navigation links."""
    archive_files = sorted(ARCHIVE_DIR.glob("*.html"), reverse=True)
    if not archive_files:
        return ""
    parts: list[str] = []
    parts.append('<div style="margin-top: 24px;">')
    parts.append('<div style="display: flex; flex-wrap: wrap; gap: 8px; justify-content: center;">')
    for f in archive_files[:30]:  # Limit to last 30 days
        date_str = f.stem  # e.g. 2026-02-14
        if not re.match(r"\d{4}-\d{2}-\d{2}", date_str):
            continue
        is_current = (date_str == current_date)
        if is_current:
            parts.append(f'<span style="padding: 4px 10px; background: var(--foreground); color: var(--background); border-radius: 6px; font-size: 12px; font-weight: 500;">{date_str}</span>')
        else:
            parts.append(f'<a href="./archive/{date_str}.html" style="padding: 4px 10px; background: var(--card); border: 1px solid var(--border); border-radius: 6px; font-size: 12px; color: var(--foreground); text-decoration: none;">{date_str}</a>')
    parts.append('</div>')
    parts.append('</div>')
    return "\n".join(parts)


def main():
    daily = load_json(DATA_DIR / "daily.json", default={})
    date = str(daily.get("date") or datetime.now(timezone.utc).strftime("%Y-%m-%d"))

    # date parts for header
    try:
        dt = datetime.strptime(date, "%Y-%m-%d")
    except Exception:
        dt = datetime.now(timezone.utc)
    date_day = str(dt.day)
    date_month = dt.strftime("%B %Y")
    date_human = f"{dt.year}年{dt.month}月{dt.day}日"

    tpl = TEMPLATE_PATH.read_text(encoding="utf-8")

    sections = daily.get("sections") or {}
    headlines = daily.get("headlines") or []

    # Map to optimized layout
    content_parts: list[str] = []

    # 1. 今日必读（核心看点，扩大展示 3-12 条）
    content_parts.append('<!-- 今日必读 -->')
    content_parts.append('<section class="section section-featured">')
    content_parts.append('<h2 class="section-title"><span>🔥</span> 今日必读</h2>')
    content_parts.append('<p style="font-size: 14px; color: var(--muted-foreground); margin-bottom: 16px;">基于 1488 条 AI 新闻筛选出的重要动态</p>')
    # Show all headlines (3-12 items)
    content_parts.append(render_cards(headlines[:12], badge_color="#dc2626"))
    content_parts.append('</section>')

    # 2. 新模型与工具（合并 releases/updates/opensource/benchmarks）
    model_tools_items = (
        (sections.get("releases") or [], "#e85d04", "发布"),
        (sections.get("updates") or [], "#4285f4", "更新"),
        (sections.get("opensource") or [], "#10a37f", "开源"),
        (sections.get("benchmarks") or [], "#8e44ad", "评测"),
    )
    has_model_tools = any(items for items, _, _ in model_tools_items)
    
    if has_model_tools:
        content_parts.append('<!-- 新模型/工具 -->')
        content_parts.append('<section class="section">')
        content_parts.append('<h2 class="section-title"><span>🚀</span> 新模型与工具</h2>')
        for items, color, tag in model_tools_items:
            if items:
                content_parts.append(render_cards(items, badge_color=color, tag=tag))
        content_parts.append('</section>')

    # 3. 企业动态
    if sections.get("business"):
        content_parts.append('<!-- 企业动态 -->')
        content_parts.append('<section class="section">')
        content_parts.append('<h2 class="section-title"><span>💼</span> 企业动态</h2>')
        content_parts.append(render_cards(sections["business"], badge_color="#7c3aed", tag="商业"))
        content_parts.append('</section>')

    # 4. 行业观察（合并 risks + 政策趋势）
    has_observation = sections.get("risks") or sections.get("policy")
    if has_observation:
        content_parts.append('<!-- 行业观察 -->')
        content_parts.append('<section class="section">')
        content_parts.append('<h2 class="section-title"><span>📰</span> 行业观察</h2>')
        content_parts.append('<p style="font-size: 14px; color: var(--muted-foreground); margin-bottom: 16px;">政策监管、市场趋势与风险信号</p>')
        if sections.get("risks"):
            content_parts.append(render_cards(sections["risks"], badge_color="#991b1b", tag="风险"))
        content_parts.append('</section>')

    # 5. X 高互动（可选，放在最后）
    x_highlights = daily.get("x_highlights")
    if x_highlights:
        content_parts.append('<!-- X 高互动 -->')
        content_parts.append('<section class="section">')
        content_parts.append(render_x_highlights(x_highlights))
        content_parts.append('</section>')

    # 6. 覆盖度自检（折叠在页脚）
    content_parts.append(render_self_check_collapsed(daily))

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

    # Generate index.html with archive navigation
    archive_nav = render_archive_nav(date)
    index_out = out.replace("{{ARCHIVE_NAV}}", archive_nav)
    (ROOT / "index.html").write_text(index_out, encoding="utf-8")

    # Also replace placeholder in archive file
    out_final = out.replace("{{ARCHIVE_NAV}}", archive_nav)
    archive_path.write_text(out_final, encoding="utf-8")

    print(str(archive_path))


if __name__ == "__main__":
    main()
