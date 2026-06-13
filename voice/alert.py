#!/usr/bin/env python3
import os
import json
import subprocess
from datetime import datetime, timedelta

def load_spoken_alerts():
    fpath = "cache/voice-alerts-spoken.json"
    if os.path.exists(fpath):
        try:
            with open(fpath, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return []

def save_spoken_alerts(alerts):
    fpath = "cache/voice-alerts-spoken.json"
    os.makedirs(os.path.dirname(fpath), exist_ok=True)
    with open(fpath, "w") as f:
        json.dump(alerts, f, indent=2)

def clean_expired_spoken(alerts):
    now = datetime.now()
    valid_alerts = []
    for alert in alerts:
        try:
            ts = datetime.fromisoformat(alert["timestamp"])
            if now - ts < timedelta(hours=4):
                valid_alerts.append(alert)
        except Exception:
            pass
    return valid_alerts

def speak_text(text):
    subprocess.run(["python3", "voice/speak.py", text])

def main():
    print("Polling JARVIS message bus for proactive voice alerts...")

    spoken_cache = load_spoken_alerts()
    spoken_cache = clean_expired_spoken(spoken_cache)
    spoken_ids = [a["message_id"] for a in spoken_cache]

    new_spoken = False

    # 1. Poll for Prime (recipient of trade_plan_ready)
    try:
        res = subprocess.run([
            "python3", "scripts/bus_poll.py", "--agent", "Prime"
        ], capture_output=True, text=True, check=True)
        messages = json.loads(res.stdout)
        
        for msg in messages:
            msg_id = msg.get("message_id")
            if msg_id not in spoken_ids:
                topic = msg.get("topic")
                payload = msg.get("payload", {})
                
                if topic == "trade_plan_ready":
                    text = f"Pardon the interruption, Jitheesh, but I've spotted a setup on {payload.get('symbol')} that looks promising. The score is {payload.get('setup_score')}, with an entry zone around {payload.get('trigger_price')}. I've prepared a full plan for you to look over whenever you have a moment."
                    speak_text(text)
                elif topic == "market_warning":
                    text = f"Just a gentle heads-up, Jitheesh. Oracle has flagged some market volatility regarding {payload.get('event')}. It might be wise to tread carefully on active positions for now."
                    speak_text(text)
                else:
                    text = f"Jitheesh — a message has arrived from {msg.get('from')} regarding {topic}."
                    speak_text(text)

                spoken_cache.append({"message_id": msg_id, "timestamp": datetime.now().isoformat()})
                spoken_ids.append(msg_id)
                new_spoken = True
    except Exception as e:
        print(f"Error polling Prime alerts: {e}")

    # 2. Poll for Synergy (recipient of infra_alert)
    try:
        res = subprocess.run([
            "python3", "scripts/bus_poll.py", "--agent", "Synergy"
        ], capture_output=True, text=True, check=True)
        messages = json.loads(res.stdout)
        
        for msg in messages:
            msg_id = msg.get("message_id")
            if msg_id not in spoken_ids:
                topic = msg.get("topic")
                payload = msg.get("payload", {})
                
                if topic == "infra_alert":
                    text = f"Jitheesh — Sentinel noticed a system event: {payload.get('event') or 'a potential issue'}. Don't worry, Synergy has already logged an urgent task to look into it."
                    speak_text(text)
                    # Create the task in memory/tasks.md
                    try:
                        subprocess.run([
                            "python3", "scripts/log_action.py", 
                            "--agent", "Synergy", 
                            "--action", f"Auto-created urgent task from infra alert: {payload.get('event')}",
                            "--message-id", msg_id
                        ], check=True)
                    except Exception:
                        pass
                else:
                    text = f"Notice. Synergy received a {topic} message from {msg.get('from')}."
                    speak_text(text)

                spoken_cache.append({"message_id": msg_id, "timestamp": datetime.now().isoformat()})
                spoken_ids.append(msg_id)
                new_spoken = True
    except Exception as e:
        print(f"Error polling Synergy alerts: {e}")

    if new_spoken:
        save_spoken_alerts(spoken_cache)
    else:
        print("No new alerts to speak.")

if __name__ == "__main__":
    main()
