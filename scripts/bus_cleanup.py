#!/usr/bin/env python3
import os
import json
from datetime import datetime, timedelta

def main():
    bus_dir = "cache/bus"
    inbox_dir = os.path.join(bus_dir, "inbox")
    processed_dir = os.path.join(bus_dir, "processed")
    broadcast_dir = os.path.join(bus_dir, "broadcast")

    now = datetime.now()
    deleted_count = 0

    for folder in [inbox_dir, processed_dir, broadcast_dir]:
        if not os.path.exists(folder):
            continue
        for fname in os.listdir(folder):
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(folder, fname)
            try:
                with open(fpath, "r") as f:
                    msg = json.load(f)
                
                timestamp_str = msg.get("timestamp")
                ttl_hours = msg.get("ttl_hours", 4)
                
                timestamp = datetime.fromisoformat(timestamp_str)
                if timestamp.tzinfo is not None:
                    timestamp = timestamp.astimezone().replace(tzinfo=None)
                expiration_time = timestamp + timedelta(hours=ttl_hours)
                
                if now > expiration_time:
                    os.remove(fpath)
                    deleted_count += 1
            except Exception as e:
                print(f"Error checking expiration for {fname}: {e}")

    # Also clean up read_broadcasts tracking files that are older
    for fname in os.listdir(bus_dir):
        if fname.startswith("read_broadcasts_") and fname.endswith(".json"):
            fpath = os.path.join(bus_dir, fname)
            # if tracking file is older than 7 days, remove it
            if os.path.getmtime(fpath) < (now - timedelta(days=7)).timestamp():
                try:
                    os.remove(fpath)
                except Exception:
                    pass

    print(f"Cleanup completed: Purged {deleted_count} expired messages.")

if __name__ == "__main__":
    main()
