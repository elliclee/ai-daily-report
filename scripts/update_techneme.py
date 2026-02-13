#!/usr/bin/env python3
"""
AI Daily Report TechMeme Auto-Updater
Automatically fetches TechMeme headlines and updates the daily report.
"""

import json
import subprocess
import re
from datetime import datetime
from pathlib import Path

def fetch_technews():
    """Fetch TechMeme headlines using technews skill."""
    skill_path = Path.home() / "clawd" / "skills" / "technews"
    scraper_script = skill_path / "scripts" / "techmeme_scraper.py"
    
    try:
        result = subprocess.run(
            ["python3", str(scraper_script)],
            capture_output=True,
            text=True,
            timeout=60
        )
        data = json.loads(result.stdout)
        return data.get("stories", [])[:5]  # Top 5 stories
    except Exception as e:
        print(f"Error fetching technews: {e}")
        return []

def generate_techneme_html(stories):
    """Generate TechMeme section HTML."""
    if not stories:
        return ""
    
    html_parts = [
        '        <!-- TechMeme 当日头条 -->',
        '        <section class="section">',
        '            <h2 class="section-title">🌐 TechMeme 当日头条</h2>',
        ''
    ]
    
    tag_map = {
        "AI": "tag-hot",
        "OpenAI": "tag-hot", 
        "IPO": "tag-hot",
        "投资": "tag-hot",
        "收购": "tag-new",
        "财报": "",
        "中国": "",
        "模型": "tag-new"
    }
    
    for story in stories[:5]:
        title = story.get("title", "").split("(")[0].strip()
        url = story.get("url", "")
        summary = story.get("summary", "")[:150] + "..." if len(story.get("summary", "")) > 150 else story.get("summary", "")
        timestamp = story.get("timestamp", "")
        
        # Determine tag
        tag_class = ""
        tag_text = "科技"
        for keyword, tclass in tag_map.items():
            if keyword in title or keyword in summary:
                tag_class = tclass
                tag_text = keyword
                break
        
        html_parts.extend([
            '            <article class="news-item">',
            f'                <span class="tag {tag_class}">{tag_text}</span>' if tag_class else f'                <span class="tag">{tag_text}</span>',
            f'                <h3 class="news-title">{title}</h3>',
            f'                <div class="news-meta">TechMeme · {timestamp[:16] if timestamp else "Today"}</div>',
            f'                <div class="news-desc">{summary}</div>',
            f'                <a class="news-link" href="{url}" target="_blank">阅读更多 →</a>',
            '            </article>',
            ''
        ])
    
    html_parts.append('        </section>')
    return '\n'.join(html_parts)

def update_daily_report(techneme_html):
    """Update the index.html with new TechMeme section."""
    report_path = Path.home() / "clawd" / "ai-daily-report" / "index.html"
    
    with open(report_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find and replace existing TechMeme section or insert before "新模型/工具"
    techneme_pattern = r'        <!-- TechMeme 当日头条 -->.*?        </section>\n\n        <!-- 新模型/工具 -->'
    replacement = techneme_html + '\n\n        <!-- 新模型/工具 -->'
    
    if re.search(techneme_pattern, content, re.DOTALL):
        content = re.sub(techneme_pattern, replacement, content, flags=re.DOTALL)
    else:
        # Insert before 新模型/工具 section
        content = content.replace(
            '        <!-- 新模型/工具 -->',
            techneme_html + '\n\n        <!-- 新模型/工具 -->'
        )
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Updated {report_path}")

def git_push():
    """Commit and push changes."""
    report_dir = Path.home() / "clawd" / "ai-daily-report"
    
    try:
        subprocess.run(
            ["git", "add", "index.html"],
            cwd=report_dir,
            check=True
        )
        subprocess.run(
            ["git", "commit", "-m", f"Auto-update TechMeme headlines - {datetime.now().strftime('%Y-%m-%d')}"],
            cwd=report_dir,
            check=True
        )
        subprocess.run(
            ["git", "push"],
            cwd=report_dir,
            check=True
        )
        print("Changes pushed to GitHub")
    except subprocess.CalledProcessError as e:
        print(f"Git operation failed: {e}")

def main():
    print(f"[{datetime.now()}] Starting TechMeme auto-update...")
    
    # Fetch TechMeme stories
    stories = fetch_technews()
    if not stories:
        print("No stories fetched, aborting")
        return
    
    print(f"Fetched {len(stories)} stories")
    
    # Generate HTML
    html = generate_techneme_html(stories)
    
    # Update report
    update_daily_report(html)
    
    # Push to GitHub
    git_push()
    
    print(f"[{datetime.now()}] TechMeme update completed")

if __name__ == "__main__":
    main()
