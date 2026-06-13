#!/usr/bin/env python3
"""Fetch India/Kerala-focused video digest via YouTube RSS (no API key)."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import feedparser

sys.path.insert(0, os.path.dirname(__file__))
from news_utils import enrich_item, sort_by_date  # noqa: E402

# India news & tech channels (public RSS)
CHANNELS = {
    "WION": "https://www.youtube.com/feeds/videos.xml?channel_id=UCQpw3xqfaMEyxAtKfQH3p1Q",
    "NDTV": "https://www.youtube.com/feeds/videos.xml?channel_id=UC9u6WCi9jyfZ2cLZiK9mCoA",
    "CNBC-TV18": "https://www.youtube.com/feeds/videos.xml?channel_id=UC7p8a4m8kk8i9zpfHCTD_8A",
    "Bloomberg India": "https://www.youtube.com/feeds/videos.xml?channel_id=UCm2JzFGXy_5vHA8cR3GJd3g",
    "Fireship Tech": "https://www.youtube.com/feeds/videos.xml?channel_id=UCsBjURrPoezykLs9EqgamOA",
}


def main():
    items = []
    seen = set()
    for name, url in CHANNELS.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:6]:
                vid_id = entry.get("yt_videoid") or entry.get("id", "").split(":")[-1]
                title = (entry.get("title") or "").strip()
                if not title or title.lower() in seen:
                    continue
                seen.add(title.lower())
                link = entry.get("link") or f"https://www.youtube.com/watch?v={vid_id}"
                published = entry.get("published") or entry.get("updated") or ""
                item = enrich_item({
                    "source": name,
                    "title": title,
                    "link": link,
                    "published": published,
                    "type": "video",
                    "video_id": vid_id,
                    "thumbnail": f"https://i.ytimg.com/vi/{vid_id}/hqdefault.jpg" if vid_id else "",
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                })
                items.append(item)
        except Exception as exc:
            print(f"  skip {name}: {exc}")

    items = sort_by_date(items)
    out_dir = Path("cache/briefings")
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "item_count": len(items),
        "items": items,
    }
    path = out_dir / "media-digest.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")
    print(f"Saved {len(items)} media items → {path}")


if __name__ == "__main__":
    main()
