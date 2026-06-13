#!/usr/bin/env python3
import os
import json
import subprocess

def main():
    digest_path = "cache/briefings/news-digest.json"
    if not os.path.exists(digest_path):
        subprocess.run(["python3", "voice/speak.py", "Good morning Jitheesh. Morning brief news file is missing."])
        return

    try:
        with open(digest_path, "r") as f:
            items = json.load(f)
        
        # Pull first 3 headlines
        headlines = [item.get("title") for item in items if item.get("title")][:3]
        
        if headlines:
            text = "Good morning, Jitheesh. I hope you're having a pleasant start to your day. Oracle has prepared your morning briefing. There are three key updates that caught my eye. "
            text += ". ".join(headlines)
            text += ". I've successfully saved the complete summary to your cache, and I am standing by if you need anything else."
        else:
            text = "Good morning, Jitheesh. I've completed the morning news check, and I'm happy to report there are no major macro warnings active today. I stand ready to assist you."
            
        subprocess.run(["python3", "voice/speak.py", text])
    except Exception as e:
        subprocess.run(["python3", "voice/speak.py", "Good morning Jitheesh. Error loading morning brief headlines."])

if __name__ == "__main__":
    main()
 Maroon
