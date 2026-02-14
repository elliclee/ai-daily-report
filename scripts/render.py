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
    sc = daily.get("self_check") or {}

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

    # --- 栏目统计 ---
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

    # --- 命中厂商（优先 self_check.coverage_analysis，fallback vendorsHit）---
    ca = sc.get("coverage_analysis") or {}
    hit_vendors = ca.get("hit_vendors") or daily.get("vendorsHit") or []
    missed_vendors = ca.get("missed_vendors") or []
    missed_reason = ca.get("missed_reason") or ""

    if hit_vendors or missed_vendors:
        parts.append('<div class="highlight-box">')
        parts.append('<div class="highlight-title">命中厂商清单</div>')
        parts.append('<p style="font-size: 13px; line-height: 1.8; margin-top: 8px;">')
        if hit_vendors:
            parts.append(" ".join([f'<span class="tag">✅ {html_escape(str(v))}</span>' for v in hit_vendors]))
        if missed_vendors:
            parts.append('<br/>')
            parts.append(" ".join([f'<span class="tag">❌ {html_escape(str(v))}</span>' for v in missed_vendors]))
        parts.append('</p>')
        if missed_reason:
            parts.append(f'<p style="font-size: 12px; color: var(--muted-foreground); margin-top: 8px;">{html_escape(str(missed_reason))}</p>')
        parts.append('</div>')

    # --- 时效检查 ---
    fc = sc.get("freshness_check") or {}
    if fc:
        parts.append('<div class="highlight-box">')
        parts.append('<div class="highlight-title">时效检查</div>')
        parts.append('<ul class="highlight-list">')
        target = fc.get("target_headlines", "?")
        actual = fc.get("actual_headlines", "?")
        parts.append(f'<li><span>📰</span><div>目标 {target} 条，实际 {actual} 条</div></li>')
        supp = fc.get("supplement_searches_triggered", False)
        supp_count = fc.get("supplement_searches_count", 0)
        parts.append(f'<li><span>🔍</span><div>补搜: {"已触发" if supp else "未触发"}（{supp_count} 次）</div></li>')
        reason = fc.get("reason", "")
        if reason:
            parts.append(f'<li><span>💡</span><div>{html_escape(str(reason))}</div></li>')
        parts.append('</ul>')
        parts.append('</div>')

    # --- Bird 状态 ---
    bs = sc.get("bird_status") or {}
    if bs:
        parts.append('<div class="highlight-box">')
        parts.append('<div class="highlight-title">X (Bird) 状态</div>')
        parts.append('<ul class="highlight-list">')
        available = bs.get("available", False)
        cookies = bs.get("cookies_found", False)
        fallback = bs.get("fallback", "")
        xsource = bs.get("x_highlights_source", "")
        parts.append(f'<li><span>🐦</span><div>可用: {"是" if available else "否"} · Cookies: {"有" if cookies else "无"}</div></li>')
        if fallback:
            parts.append(f'<li><span>🔄</span><div>Fallback: {html_escape(str(fallback))}</div></li>')
        if xsource:
            parts.append(f'<li><span>📝</span><div>{html_escape(str(xsource))}</div></li>')
        parts.append('</ul>')
        parts.append('</div>')

    # --- Dedupe Keys（优先结构化，fallback 字符串数组）---
    dedup_keys = sc.get("dedupe_keys") or []
    dedup_strs = daily.get("dedupKeys") or []
    if dedup_keys:
        parts.append('<div class="highlight-box">')
        parts.append('<div class="highlight-title">Deduplicate Keys</div>')
        parts.append('<ul class="highlight-list">')
        for dk in dedup_keys:
            if isinstance(dk, dict):
                key = html_escape(str(dk.get("key", "")))
                entity = html_escape(str(dk.get("entity", "")))
                product = html_escape(str(dk.get("product", "")))
                merged = dk.get("sources_merged", "")
                parts.append(f'<li><span>🔑</span><div><strong>{key}</strong> — {entity}/{product}')
                if merged:
                    parts.append(f' ({merged}源合并)')
                parts.append('</div></li>')
            else:
                parts.append(f'<li><span>🔑</span><div>{html_escape(str(dk))}</div></li>')
        parts.append('</ul>')
        parts.append('</div>')
    elif dedup_strs:
        parts.append('<div class="highlight-box">')
        parts.append('<div class="highlight-title">Deduplicate Keys</div>')
        parts.append('<p style="font-size: 12px; line-height: 1.6; margin-top: 8px; color: var(--muted-foreground);">')
        parts.append(html_escape(" | ".join(str(d) for d in dedup_strs)))
        parts.append('</p>')
        parts.append('</div>')

    # --- 降级条目 ---
    downgraded = sc.get("downgraded_entries") or []
    if downgraded:
        parts.append('<div class="highlight-box">')
        parts.append('<div class="highlight-title">降级/观察条目</div>')
        parts.append('<ul class="highlight-list">')
        for de in downgraded:
            if isinstance(de, dict):
                title = html_escape(str(de.get("title", "")))
                reason = html_escape(str(de.get("reason", "")))
                parts.append(f'<li><span>👁️</span><div><strong>{title}</strong>：{reason}</div></li>')
            else:
                parts.append(f'<li><span>👁️</span><div>{html_escape(str(de))}</div></li>')
        parts.append('</ul>')
        parts.append('</div>')

    parts.append('</section>')
    return "\n".join(parts)


def render_archive_nav(current_date: str) -> str:
    """Scan archive/ directory and generate navigation links."""
    archive_files = sorted(ARCHIVE_DIR.glob("*.html"), reverse=True)
    if not archive_files:
        return ""
    parts: list[str] = []
    parts.append('<div style="margin-top: 24px;">')
    parts.append('<div style="display: flex; flex-wrap: wrap; gap: 8px; justify-content: center;">')
    for f in archive_files:
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
    date = str(daily.get("date") or datetime.utcnow().strftime("%Y-%m-%d"))

    # date parts for header
    try:
        dt = datetime.strptime(date, "%Y-%m-%d")
    except Exception:
        dt = datetime.utcnow()
    date_day = str(dt.day)
    date_month = dt.strftime("%B %Y")
    date_human = f"{dt.year}年{dt.month}月{dt.day}日"

    tpl = TEMPLATE_PATH.read_text(encoding="utf-8")

    sections = daily.get("sections") or {}

    # Map to 2026-02-13 style sections
    content_parts: list[str] = []

    # 2/13 ordering:
    # 核心看点(偏头条、少而精) → TechMeme 头条 → 新模型/工具(+X高互动) → 企业动态 → 风险/事故 → 覆盖度自检

    # 核心看点：默认只展示前 3 条（与 2/13 的信息密度一致）
    content_parts.append('<!-- 核心看点 -->')
    content_parts.append('<section class="section">')
    content_parts.append('<h2 class="section-title"><span>🔥</span> 核心看点</h2>')
    content_parts.append(render_cards((daily.get("headlines") or [])[:5]))
    content_parts.append('</section>')

    # TechMeme 当日头条（从 data/techneme.json 或 daily.techmeme_headlines 读取；没有则不显示）
    techmeme = load_json(DATA_DIR / "techneme.json", default={})

    # Accept multiple shapes:
    # - daily.techmeme_headlines: [string|{text}]
    # - data/*: {headlines:[...]}
    # - data/*: {stories:[{title,url,summary}]}
    tm_list = daily.get("techmeme_headlines") or techmeme.get("headlines") or techmeme.get("stories") or []

    if tm_list:
        content_parts.append('<!-- TechMeme 头条 -->')
        content_parts.append('<section class="section">')
        content_parts.append('<h2 class="section-title"><span>🌐</span> TechMeme 当日头条</h2>')
        content_parts.append('<div class="highlight-box">')
        content_parts.append('<ul class="highlight-list">')
        for it in tm_list[:5]:
            if isinstance(it, str):
                text = it
            else:
                d = it or {}
                text = str(d.get("text") or d.get("title") or "")
            if text.strip():
                content_parts.append(f'<li><span>⚡</span><div>{html_escape(text.strip())}</div></li>')
        content_parts.append('</ul>')
        content_parts.append('</div>')
        content_parts.append('</section>')

    # 新模型/工具：按栏目分别渲染，保证每条卡片有 tag（发布/更新/开源/评测）
    content_parts.append('<!-- 新模型/工具 -->')
    content_parts.append('<section class="section">')
    content_parts.append('<h2 class="section-title"><span>🚀</span> 新模型/工具</h2>')
    content_parts.append(render_cards(sections.get("releases") or [], badge_color="#e85d04", tag="发布"))
    content_parts.append(render_cards(sections.get("updates") or [], badge_color="#4285f4", tag="更新"))
    content_parts.append(render_cards(sections.get("opensource") or [], badge_color="#10a37f", tag="开源"))
    content_parts.append(render_cards(sections.get("benchmarks") or [], badge_color="#8e44ad", tag="评测"))

    # X 高互动事件：放在新模型/工具 section 内部（与 2/13 更一致）
    content_parts.append(render_x_highlights(daily.get("x_highlights")))

    content_parts.append('</section>')

    # 企业动态
    content_parts.append('<!-- 企业动态 -->')
    content_parts.append('<section class="section">')
    content_parts.append('<h2 class="section-title"><span>💼</span> 企业动态</h2>')
    content_parts.append(render_cards(sections.get("business") or [], badge_color="#1f1d1a", tag="商业"))
    content_parts.append('</section>')

    # 风险/事故
    content_parts.append('<!-- 风险/事故 -->')
    content_parts.append('<section class="section">')
    content_parts.append('<h2 class="section-title"><span>⚠️</span> 风险/事故</h2>')
    content_parts.append(render_cards(sections.get("risks") or [], badge_color="#c0392b", tag="风险"))
    content_parts.append('</section>')

    # 覆盖度自检
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

    # Generate index.html with archive navigation
    archive_nav = render_archive_nav(date)
    index_out = out.replace("{{ARCHIVE_NAV}}", archive_nav)
    (ROOT / "index.html").write_text(index_out, encoding="utf-8")

    # Also replace placeholder in archive file (no nav needed there, or same nav)
    out_final = out.replace("{{ARCHIVE_NAV}}", archive_nav)
    archive_path.write_text(out_final, encoding="utf-8")

    print(str(archive_path))


if __name__ == "__main__":
    main()
