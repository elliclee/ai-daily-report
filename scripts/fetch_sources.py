#!/usr/bin/env python3
"""
AI Daily Report - Multi-Source Fetcher
Fetches content from configured sources (RSS, HN, Reddit, GitHub Trending).
Twitter sources are handled separately via bird CLI.
"""

import json
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
import re
import ssl

# SSL context for HTTPS requests
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE


def load_sources():
    """Load sources configuration."""
    config_path = Path(__file__).parent.parent / "sources.json"
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def fetch_url(url, timeout=30):
    """Fetch URL content with error handling."""
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; AI-Daily-Report/1.0)"
            }
        )
        with urllib.request.urlopen(req, timeout=timeout, context=ssl_context) as response:
            return response.read().decode("utf-8")
    except Exception as e:
        print(f"  Error fetching {url}: {e}")
        return None


def extract_description(html):
    """Extract description from HTML (meta description, og:description, or first paragraph)."""
    if not html:
        return ""
    
    # Try og:description first (usually better quality)
    og_desc = re.search(r'<meta[^>]*property=["\']og:description["\'][^>]*content=["\']([^"\']+)["\']', html, re.IGNORECASE)
    if og_desc:
        return og_desc.group(1).strip()
    
    og_desc = re.search(r'<meta[^>]*content=["\']([^"\']+)["\'][^>]*property=["\']og:description["\']', html, re.IGNORECASE)
    if og_desc:
        return og_desc.group(1).strip()
    
    # Try meta description
    meta_desc = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']+)["\']', html, re.IGNORECASE)
    if meta_desc:
        return meta_desc.group(1).strip()
    
    meta_desc = re.search(r'<meta[^>]*content=["\']([^"\']+)["\'][^>]*name=["\']description["\']', html, re.IGNORECASE)
    if meta_desc:
        return meta_desc.group(1).strip()
    
    return ""


def fetch_json(url, timeout=30):
    """Fetch JSON from URL."""
    content = fetch_url(url, timeout)
    if content:
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            print(f"  Error parsing JSON: {e}")
    return None


def fetch_hackernews(config):
    """Fetch Hacker News top stories."""
    print(f"  Fetching HN: filter={config.get('filter')}, min_score={config.get('min_score')}")
    
    # Get top story IDs
    stories_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
    story_ids = fetch_json(stories_url)
    
    if not story_ids:
        return []
    
    min_score = config.get("min_score", 100)
    limit = config.get("limit", 10)
    fetch_desc = config.get("fetch_description", True)
    
    items = []
    for sid in story_ids[:30]:  # Check top 30 to find enough qualifying stories
        if len(items) >= limit:
            break
        
        story_url = f"https://hacker-news.firebaseio.com/v0/item/{sid}.json"
        story = fetch_json(story_url)
        
        if story and story.get("score", 0) >= min_score and story.get("url"):
            item = {
                "title": story.get("title", ""),
                "url": story.get("url", ""),
                "score": story.get("score", 0),
                "by": story.get("by", ""),
                "time": datetime.fromtimestamp(story.get("time", 0)).isoformat(),
                "comments": f"https://news.ycombinator.com/item?id={sid}"
            }
            
            # Fetch description from the article
            if fetch_desc:
                html = fetch_url(item["url"], timeout=10)
                item["description"] = extract_description(html)[:300] if html else ""
            else:
                item["description"] = ""
            
            items.append(item)
    
    return items


def fetch_reddit(config):
    """Fetch Reddit posts from a subreddit."""
    subreddit = config.get("subreddit", "all")
    sort = config.get("sort", "hot")
    limit = config.get("limit", 10)
    
    print(f"  Fetching Reddit: r/{subreddit}, sort={sort}")
    
    url = f"https://www.reddit.com/r/{subreddit}/{sort}.json?limit={limit * 2}"
    data = fetch_json(url)
    
    if not data or "data" not in data:
        return []
    
    items = []
    for child in data["data"].get("children", []):
        post = child.get("data", {})
        if post.get("score", 0) >= 50:  # Minimum score filter
            items.append({
                "title": post.get("title", ""),
                "url": post.get("url", ""),
                "score": post.get("score", 0),
                "author": post.get("author", ""),
                "subreddit": post.get("subreddit", ""),
                "num_comments": post.get("num_comments", 0),
                "permalink": f"https://reddit.com{post.get('permalink', '')}"
            })
        
        if len(items) >= limit:
            break
    
    return items


def fetch_github_trending(config):
    """Fetch GitHub trending repositories."""
    language = config.get("language", "")
    since = config.get("since", "daily")
    limit = config.get("limit", 5)
    fetch_desc = config.get("fetch_description", True)
    
    print(f"  Fetching GitHub Trending: lang={language or 'all'}, since={since}")
    
    # GitHub doesn't have a proper API for trending, so we scrape the HTML
    url = f"https://github.com/trending/{language}?since={since}"
    content = fetch_url(url)
    
    if not content:
        return []
    
    items = []
    
    # Split by article tags (each repo is an article)
    articles = content.split('<article class="Box-row"')
    
    for article in articles[1:]:  # Skip first empty split
        if len(items) >= limit:
            break
            
        # Extract repo path from h2 > a link
        repo_match = re.search(r'<h2[^>]*>.*?<a[^>]*href="/([^"]+)"[^>]*>', article, re.DOTALL)
        if not repo_match:
            continue
        
        repo_path = repo_match.group(1).strip()
        
        # Skip non-repo links (login, sponsors, etc.)
        if repo_path.startswith("login") or repo_path.startswith("sponsors"):
            continue
        
        # Extract description from trending page
        desc_match = re.search(r'<p[^>]*class="[^"]*col-9[^"]*"[^>]*>(.*?)</p>', article, re.DOTALL)
        description = desc_match.group(1).strip().replace("\n", " ") if desc_match else ""
        
        # Clean up HTML entities
        description = description.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
        
        # If no description from trending page, fetch repo page
        if not description and fetch_desc:
            repo_html = fetch_url(f"https://github.com/{repo_path}", timeout=10)
            if repo_html:
                # Try og:description from repo page
                description = extract_description(repo_html)[:300]
        
        # Extract stars today
        stars_match = re.search(r'([0-9,]+)\s*stars?\s+today', article)
        stars_today = stars_match.group(1).replace(",", "") if stars_match else "0"
        
        # Extract language
        lang_match = re.search(r'<span[^>]*itemprop="programmingLanguage"[^>]*>([^<]+)</span>', article)
        lang = lang_match.group(1).strip() if lang_match else ""
        
        items.append({
            "repo": repo_path,
            "name": repo_path.split("/")[-1],
            "url": f"https://github.com/{repo_path}",
            "description": description,
            "stars_today": stars_today,
            "language": lang
        })
    
    return items


def fetch_rss(config):
    """Fetch RSS/Atom feed."""
    url = config.get("url")
    limit = config.get("limit", 10)
    
    if not url:
        return []
    
    print(f"  Fetching RSS: {url}")
    
    content = fetch_url(url)
    if not content:
        return []
    
    items = []
    try:
        root = ET.fromstring(content)
        
        # Handle both RSS and Atom formats
        # RSS: <channel><item>
        # Atom: <entry>
        
        entries = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
        
        for entry in entries[:limit]:
            title_elem = entry.find("title")
            if title_elem is None:
                title_elem = entry.find("{http://www.w3.org/2005/Atom}title")
            
            link_elem = entry.find("link")
            if link_elem is None:
                link_elem = entry.find("{http://www.w3.org/2005/Atom}link")
            
            desc_elem = entry.find("description")
            if desc_elem is None:
                desc_elem = entry.find("{http://www.w3.org/2005/Atom}summary")
            
            pubdate_elem = entry.find("pubDate")
            if pubdate_elem is None:
                pubdate_elem = entry.find("{http://www.w3.org/2005/Atom}published")
            
            title = title_elem.text if title_elem is not None else ""
            
            # Atom links have href attribute
            if link_elem is not None:
                link = link_elem.get("href") or link_elem.text or ""
            else:
                link = ""
            
            description = desc_elem.text if desc_elem is not None else ""
            pubdate = pubdate_elem.text if pubdate_elem is not None else ""
            
            if title and link:
                items.append({
                    "title": title.strip(),
                    "url": link.strip(),
                    "description": description.strip()[:300],
                    "published": pubdate.strip()
                })
    except ET.ParseError as e:
        print(f"  Error parsing RSS: {e}")
    
    return items


def fetch_all():
    """Fetch all enabled sources."""
    config = load_sources()
    sources = config.get("sources", [])
    
    results = {
        "fetched_at": datetime.now().isoformat(),
        "sources": {}
    }
    
    fetchers = {
        "hackernews": fetch_hackernews,
        "reddit": fetch_reddit,
        "github_trending": fetch_github_trending,
        "rss": fetch_rss
    }
    
    for source in sources:
        if not source.get("enabled", False):
            print(f"Skipping disabled source: {source.get('id')}")
            continue
        
        source_id = source.get("id")
        source_type = source.get("type")
        source_config = source.get("config", {})
        
        print(f"\nFetching {source_id} ({source_type})...")
        
        fetcher = fetchers.get(source_type)
        if fetcher:
            items = fetcher(source_config)
            results["sources"][source_id] = {
                "type": source_type,
                "count": len(items),
                "items": items
            }
            print(f"  Got {len(items)} items")
        else:
            print(f"  Unknown source type: {source_type}")
    
    return results


def main():
    print(f"[{datetime.now()}] Starting source fetch...")
    
    results = fetch_all()
    
    # Save to file
    output_path = Path(__file__).parent.parent / "data" / "fetched_sources.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n[{datetime.now()}] Fetch completed")
    print(f"Saved to: {output_path}")
    
    # Summary
    total = sum(s["count"] for s in results["sources"].values())
    print(f"Total items: {total}")
    
    return results


if __name__ == "__main__":
    main()
