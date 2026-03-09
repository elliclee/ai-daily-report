#!/usr/bin/env python3
"""修复 daily.json：从新格式转换为旧格式"""
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"

def main():
    # 读取新格式数据
    new_path = DATA_DIR / "daily" / "2026-03-09.json"
    with open(new_path, "r", encoding="utf-8") as f:
        new_data = json.load(f)
    
    # 转换为旧格式
    old = {
        "date": new_data["date"],
        "summary": {
            "title": f"AI日报 {new_data['date']}",
            "url": "https://elliclee.github.io/ai-daily-report/",
            "archiveUrl": f"https://elliclee.github.io/ai-daily-report/archive/{new_data['date']}.html"
        },
        "headlines": [],
        "sections": {
            "releases": [],
            "updates": [],
            "opensource": [],
            "benchmarks": [],
            "business": [],
            "risks": []
        },
        "x_highlights": [],
        "self_check": {
            "freshness_check": {
                "target_headlines": 12,
                "actual_headlines": len(new_data.get("top_stories", [])),
                "supplement_searches_triggered": False,
                "supplement_searches_count": 0,
                "rejected_over_48h": [],
                "reason": "从新格式转换"
            },
            "coverage_analysis": {},
            "bird_status": {"available": True},
            "dedupe_keys": [],
            "rejected_entries": []
        }
    }
    
    # 转换 top_stories 为 headlines
    for story in new_data.get("top_stories", [])[:12]:
        headline = {
            "title": story["title"],
            "time": story.get("published_date", new_data["date"]),
            "what": story.get("summary", "")[:300],
            "why": "",
            "sources": [{
                "name": story.get("source", "Unknown"),
                "url": story.get("source_url", "")
            }]
        }
        old["headlines"].append(headline)
        
        # 同时按分类放入 sections
        cat = story.get("category", "")
        item = {
            "title": story["title"],
            "time": story.get("published_date", new_data["date"]),
            "what": story.get("summary", "")[:300],
            "why": "",
            "sources": [{
                "name": story.get("source", "Unknown"),
                "url": story.get("source_url", "")
            }]
        }
        
        if cat == "模型发布":
            old["sections"]["releases"].append(item)
        elif cat == "产品发布":
            old["sections"]["updates"].append(item)
        elif cat == "开源":
            old["sections"]["opensource"].append(item)
        elif cat == "评测":
            old["sections"]["benchmarks"].append(item)
        elif cat in ["行业动态", "商业"]:
            old["sections"]["business"].append(item)
        elif cat == "风险":
            old["sections"]["risks"].append(item)
    
    # 转换 x_highlights
    for xh in new_data.get("x_highlights", []):
        old["x_highlights"].append({
            "author": xh.get("author", ""),
            "handle": xh.get("handle", ""),
            "text": xh.get("text", "")[:200],
            "url": xh.get("url", ""),
            "likes": xh.get("likes", 0),
            "reposts": xh.get("reposts", 0),
            "replies": xh.get("replies", 0)
        })
    
    # 保存
    old_path = DATA_DIR / "daily.json"
    with open(old_path, "w", encoding="utf-8") as f:
        json.dump(old, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 已转换: {old_path}")
    
    # 验证
    try:
        with open(old_path, "r") as f:
            json.load(f)
        print("✅ JSON 格式有效")
    except json.JSONDecodeError as e:
        print(f"❌ JSON 格式错误: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
