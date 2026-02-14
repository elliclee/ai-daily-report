#!/usr/bin/env python3
"""
Migrate historical archive HTML files to the new Claude-like template style.

Strategy:
- For each old archive HTML (Feb 5-13), extract the body content between
  <div class="container"> tags (excluding old header, footer, and <style> block).
- Extract only the <section> elements (the actual news content).
- Wrap them in the new template.html's CSS + header + footer.
- Preserve all news content and structure.

For Feb 14 (already rendered via render.py), skip it.
"""

import re
import sys
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent
ARCHIVE_DIR = ROOT / "archive"
TEMPLATE_PATH = ROOT / "template.html"


def extract_date_from_filename(filename: str) -> str:
    """Extract date string from filename like '2026-02-06.html'."""
    return filename.replace(".html", "")


def date_to_chinese(date_str: str) -> str:
    """Convert '2026-02-06' to '2026年2月6日'."""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return f"{dt.year}年{dt.month}月{dt.day}日"


def extract_body_content(html: str) -> str:
    """
    Extract all <section> blocks and similar content blocks from old HTML.
    Also extract check-section, dedupe-list, and other content blocks.
    """
    # Find everything inside <div class="container"> but skip header and footer
    container_match = re.search(
        r'<div\s+class="container">\s*(.+?)\s*</div>\s*</body>',
        html,
        re.DOTALL,
    )
    if not container_match:
        return ""

    container_html = container_match.group(1)

    # Remove old header block (various shapes)
    # Shape 1: <header>...</header> + <div class="page-title">...</div>
    container_html = re.sub(r'<header>.*?</header>', '', container_html, flags=re.DOTALL)
    container_html = re.sub(r'<div\s+class="page-title">.*?</div>', '', container_html, flags=re.DOTALL)

    # Remove old footer
    container_html = re.sub(r'<footer>.*?</footer>', '', container_html, flags=re.DOTALL)

    # Clean up excessive whitespace
    container_html = re.sub(r'\n{3,}', '\n\n', container_html.strip())

    return container_html


def normalize_content(content: str) -> str:
    """
    Normalize old HTML content classes to match the new template's CSS.
    The new template uses these class names:
    - .section, .section-title, .card, .card-title, .card-content, .card-meta, .card-sources
    - .highlight-box, .highlight-list
    - .x-highlight, .x-item, .x-avatar, .x-content, .x-author, .x-handle, .x-engagement

    Old HTML uses:
    - section (no class), .section-title, .news-item, h3, p, .news-source, .news-tag
    - .highlight-box, .check-section, .check-list
    - .x-card, .x-header, .x-name, .x-handle, .x-content, .x-stats
    """

    # Wrap bare <section> tags with class="section"
    content = re.sub(r'<section(?!\s+class)>', '<section class="section">', content)

    # Normalize news-item divs/articles to cards
    content = content.replace('class="news-item"', 'class="card"')

    # Normalize news titles to card titles
    # Old: <h3>...</h3> or <div class="news-title">
    content = re.sub(
        r'<div\s+class="news-title">',
        '<div class="card-title">',
        content
    )

    # Normalize news descriptions to card content
    content = re.sub(
        r'<div\s+class="news-desc">',
        '<div class="card-content">',
        content
    )

    # Normalize news time to card meta
    content = re.sub(
        r'<div\s+class="news-time">',
        '<div class="card-meta">',
        content
    )

    # Normalize news source to card sources
    content = content.replace('class="news-source"', 'class="card-sources"')
    content = content.replace('class="news-sources"', 'class="card-sources"')

    # Normalize news-tag to tag
    content = content.replace('class="news-tag"', 'class="tag"')

    # Normalize tag.highlight to tag-hot
    content = content.replace('class="tag highlight"', 'class="tag tag-hot"')

    # Normalize check-section → highlight-box
    content = re.sub(r'class="check-section"[^>]*>', 'class="highlight-box">', content)
    content = content.replace('class="check-title"', 'class="highlight-title"')
    content = content.replace('class="check-list"', 'class="highlight-list"')

    # Normalize x-card → x-highlight
    content = content.replace('class="x-card"', 'class="card"')
    content = content.replace('class="x-header"', 'class="card-meta"')
    content = content.replace('class="x-name"', 'class="x-author"')
    content = content.replace('class="x-stats"', 'class="x-engagement"')

    # Normalize archive section
    content = re.sub(r'<(?:section|div)\s+class="archive"[^>]*>.*?</(?:section|div)>', '', content, flags=re.DOTALL)

    # Normalize dedupe-list (keep as highlight-box)
    content = content.replace('class="dedupe-list"', 'class="highlight-box"')

    # Remove any leftover inline style attributes that conflict with new template
    # (but keep structural ones)
    content = re.sub(r'style="[^"]*font-family[^"]*"', '', content)

    return content


def build_new_page(date_str: str, content: str) -> str:
    """Build a complete HTML page using the new template structure."""
    tpl = TEMPLATE_PATH.read_text(encoding="utf-8")
    date_chinese = date_to_chinese(date_str)
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Build archive navigation
    archive_nav = build_archive_nav(date_str)

    out = tpl
    out = out.replace("{{DATE_HUMAN}}", date_chinese)
    out = out.replace("{{CONTENT}}", content)
    out = out.replace("{{GENERATED_AT_UTC}}", now_utc)
    out = out.replace("{{ARCHIVE_NAV}}", archive_nav)

    return out


def build_archive_nav(current_date: str) -> str:
    """Generate archive navigation links."""
    archive_files = sorted(ARCHIVE_DIR.glob("*.html"), reverse=True)
    if not archive_files:
        return ""
    parts = []
    parts.append('<div style="margin-top: 24px;">')
    parts.append('<div style="display: flex; flex-wrap: wrap; gap: 8px; justify-content: center;">')
    for f in archive_files:
        date_str = f.stem
        if not re.match(r"\d{4}-\d{2}-\d{2}", date_str):
            continue
        if date_str == current_date:
            parts.append(
                f'<span style="padding: 4px 10px; background: var(--foreground); color: var(--background); '
                f'border-radius: 6px; font-size: 12px; font-weight: 500;">{date_str}</span>'
            )
        else:
            parts.append(
                f'<a href="./archive/{date_str}.html" style="padding: 4px 10px; background: var(--card); '
                f'border: 1px solid var(--border); border-radius: 6px; font-size: 12px; '
                f'color: var(--foreground); text-decoration: none;">{date_str}</a>'
            )
    parts.append('</div>')
    parts.append('</div>')
    return "\n".join(parts)


def migrate_file(filepath: Path, dry_run: bool = False) -> bool:
    """Migrate a single archive file. Returns True if successful."""
    date_str = extract_date_from_filename(filepath.name)
    print(f"  Processing {filepath.name}...")

    html = filepath.read_text(encoding="utf-8")

    # Extract content
    content = extract_body_content(html)
    if not content.strip():
        print(f"    ⚠️  No content extracted, skipping")
        return False

    # Normalize class names
    content = normalize_content(content)

    # Build new page
    new_html = build_new_page(date_str, content)

    if dry_run:
        print(f"    ✅ Would write {len(new_html)} bytes")
        return True

    # Write
    filepath.write_text(new_html, encoding="utf-8")
    print(f"    ✅ Written {len(new_html)} bytes")
    return True


def main():
    dry_run = "--dry-run" in sys.argv

    if dry_run:
        print("🔍 DRY RUN MODE — no files will be modified\n")

    # Get the latest date (rendered via render.py, already has new style)
    # We'll process everything and let the current day re-render via render.py
    skip_dates = set()

    # Find all archive files
    archive_files = sorted(ARCHIVE_DIR.glob("*.html"))
    if not archive_files:
        print("No archive files found.")
        return

    print(f"Found {len(archive_files)} archive files")

    # Get the latest date to determine which file was rendered by render.py
    # We'll skip it since it already has the new style
    latest_file = max(archive_files, key=lambda f: f.stem)
    latest_date = latest_file.stem
    skip_dates.add(latest_date)
    print(f"Skipping {latest_date} (already using new template via render.py)\n")

    success_count = 0
    skip_count = 0
    fail_count = 0

    for f in archive_files:
        date_str = f.stem
        if date_str in skip_dates:
            print(f"  Skipping {f.name} (already has new style)")
            skip_count += 1
            continue
        if migrate_file(f, dry_run=dry_run):
            success_count += 1
        else:
            fail_count += 1

    print(f"\n{'DRY RUN ' if dry_run else ''}Results:")
    print(f"  ✅ Migrated: {success_count}")
    print(f"  ⏭️  Skipped: {skip_count}")
    print(f"  ❌ Failed: {fail_count}")

    if not dry_run:
        # Also regenerate index.html to match
        print("\n📋 Re-running render.py to update index.html...")
        import subprocess
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "render.py")],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print(f"  ✅ {result.stdout.strip()}")
        else:
            print(f"  ❌ render.py failed: {result.stderr}")


if __name__ == "__main__":
    main()
