#!/usr/bin/env python3
import os
import json
import feedparser
import subprocess
from datetime import datetime

# Feeds to scan
FEEDS = {
    "HackerNews": "https://news.ycombinator.com/rss",
    "YahooFinanceMacro": "https://finance.yahoo.com/news/rssindex"
}

# High-impact news keywords
WARNING_KEYWORDS = ["RBI", "FED", "CPI", "NFP", "RATE DECISION", "INTEREST RATE", "INFLATION", "WAR", "SANCTIONS"]

def main():
    print("Fetching global macro and tech news digests...")
    
    digest_items = []
    active_warnings = []

    for name, url in FEEDS.items():
        print(f"Scanning RSS feed: {name} ({url})...")
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:10]: # Check top 10 items
                title = entry.get("title", "")
                link = entry.get("link", "")
                summary = entry.get("summary", "")
                published = entry.get("published", "")

                item = {
                    "source": name,
                    "title": title,
                    "link": link,
                    "published": published
                }
                digest_items.append(item)

                # Check for high-impact keywords
                import re
                for keyword in WARNING_KEYWORDS:
                    pattern = re.compile(r'\b' + re.escape(keyword) + r'\b', re.IGNORECASE)
                    if pattern.search(title):
                        warning_msg = f"High-Impact Keyword '{keyword}' detected in: '{title}'"
                        print(f"WARNING: {warning_msg}")
                        active_warnings.append({
                            "keyword": keyword,
                            "title": title,
                            "link": link,
                            "source": name
                        })
                        break # Only trigger once per article
        except Exception as e:
            print(f"Failed to fetch feed {name}: {e}")

    # Save digest items to cache
    briefings_dir = "cache/briefings"
    os.makedirs(briefings_dir, exist_ok=True)
    digest_path = os.path.join(briefings_dir, "news-digest.json")
    with open(digest_path, "w") as f:
        json.dump(digest_items, f, indent=2)
    print(f"Saved news digest with {len(digest_items)} items to {digest_path}")

    # Write market warnings to broadcast if detected
    if active_warnings:
        for warn in active_warnings:
            payload = {
                "symbol": "ALL",
                "event": f"Macro News Trigger: {warn['keyword']}",
                "impact": "high",
                "title": warn["title"],
                "link": warn["link"]
            }
            try:
                subprocess.run([
                    "python3", "scripts/bus_write.py",
                    "--from-agent", "Oracle",
                    "--to-agent", "broadcast",
                    "--topic", "market_warning",
                    "--payload", json.dumps(payload),
                    "--ttl-hours", "24"
                ], check=True)
            except Exception as e:
                print(f"Failed to write warning broadcast to bus: {e}")

if __name__ == "__main__":
    main()
