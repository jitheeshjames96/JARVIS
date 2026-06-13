#!/usr/bin/env python3
import os
import json
import re
import subprocess
import sys
from datetime import datetime, timezone

import feedparser

sys.path.insert(0, os.path.dirname(__file__))
from news_utils import enrich_item, sort_by_date  # noqa: E402

FEEDS = {
    "BBC World": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "Yahoo Finance": "https://finance.yahoo.com/news/rssindex",
    "Livemint India": "https://www.livemint.com/rss/markets",
    "The Hindu Business": "https://www.thehindubusinessline.com/markets/?service=rss",
    "Google India Markets": "https://news.google.com/rss/search?q=India+stock+market+NSE+RBI&hl=en-IN&gl=IN&ceid=IN:en",
    "Google Kerala": "https://news.google.com/rss/search?q=Kerala+India+news&hl=en-IN&gl=IN&ceid=IN:en",
    "Google Forex INR": "https://news.google.com/rss/search?q=USD+INR+forex+India&hl=en-IN&gl=IN&ceid=IN:en",
    "Hacker News": "https://news.ycombinator.com/rss",
    "TechCrunch": "https://techcrunch.com/feed/",
}

WARNING_KEYWORDS = [
    "RBI", "FED", "FOMC", "CPI", "NFP", "RATE DECISION", "INTEREST RATE",
    "INFLATION", "WAR", "SANCTIONS", "RECESSION", "CRASH", "TARIFF",
]

ITEMS_PER_FEED = 12


def main():
    print("Fetching live global news digests...")
    digest_items = []
    active_warnings = []
    seen_titles: set[str] = set()

    for name, url in FEEDS.items():
        print(f"  → {name}")
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:ITEMS_PER_FEED]:
                title = (entry.get("title") or "").strip()
                if not title or title.lower() in seen_titles:
                    continue
                seen_titles.add(title.lower())

                link = entry.get("link", "")
                published = entry.get("published") or entry.get("updated") or ""
                item = enrich_item({
                    "source": name,
                    "title": title,
                    "link": link,
                    "published": published,
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                })
                digest_items.append(item)

                for keyword in WARNING_KEYWORDS:
                    pattern = re.compile(r"\b" + re.escape(keyword) + r"\b", re.IGNORECASE)
                    if pattern.search(title):
                        active_warnings.append({
                            "keyword": keyword,
                            "title": title,
                            "link": link,
                            "source": name,
                            "published_display": item.get("published_display", ""),
                        })
                        break
        except Exception as e:
            print(f"  ✗ {name}: {e}")

    digest_items = sort_by_date(digest_items)

    briefings_dir = "cache/briefings"
    os.makedirs(briefings_dir, exist_ok=True)
    digest_path = os.path.join(briefings_dir, "news-digest.json")
    meta = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "feed_count": len(FEEDS),
        "item_count": len(digest_items),
        "items": digest_items,
    }
    with open(digest_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
        f.write("\n")
    print(f"Saved {len(digest_items)} news items ({digest_path})")

    if active_warnings:
        for warn in active_warnings[:3]:
            payload = {
                "symbol": "ALL",
                "event": f"Macro News Trigger: {warn['keyword']}",
                "impact": "high",
                "title": warn["title"],
                "link": warn["link"],
                "published": warn.get("published_display", ""),
            }
            try:
                subprocess.run([
                    "python3", "scripts/bus_write.py",
                    "--from-agent", "Oracle",
                    "--to-agent", "broadcast",
                    "--topic", "market_warning",
                    "--payload", json.dumps(payload),
                    "--ttl-hours", "12",
                ], check=False)
            except Exception as e:
                print(f"Bus warning write failed: {e}")


if __name__ == "__main__":
    main()
