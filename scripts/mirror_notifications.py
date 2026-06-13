#!/usr/bin/env python3
import os
import json
import yaml
import argparse
import urllib.request
import urllib.parse

def get_arg_parser():
    parser = argparse.ArgumentParser(description="Mirror bus notifications to Slack or Telegram.")
    parser.add_argument("--dry-run", action="store_true", help="Print notification payloads instead of sending them")
    return parser

def load_notifications_config():
    fpath = "config/notifications.yaml"
    if not os.path.exists(fpath):
        fpath = "config/notifications.yaml.example"
    with open(fpath, "r") as f:
        return yaml.safe_load(f)

def load_sent_notifications():
    fpath = "cache/notifications-sent.json"
    if os.path.exists(fpath):
        try:
            with open(fpath, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return []

def save_sent_notifications(sent):
    fpath = "cache/notifications-sent.json"
    os.makedirs(os.path.dirname(fpath), exist_ok=True)
    with open(fpath, "w") as f:
        json.dump(sent, f, indent=2)

def send_telegram(token, chat_id, text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode("utf-8")
    req = urllib.request.Request(url, data=data)
    with urllib.request.urlopen(req) as response:
        return response.read()

def send_slack(webhook_url, text):
    req = urllib.request.Request(
        webhook_url,
        data=json.dumps({"text": text}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as response:
        return response.read()

def main():
    parser = get_arg_parser()
    args = parser.parse_args()

    config = load_notifications_config()
    sent_list = load_sent_notifications()

    bus_dir = "cache/bus"
    inbox_dir = os.path.join(bus_dir, "inbox")
    processed_dir = os.path.join(bus_dir, "processed")
    broadcast_dir = os.path.join(bus_dir, "broadcast")

    new_notifications = []

    # Scan for new messages
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
                
                msg_id = msg.get("message_id")
                if msg_id not in sent_list:
                    topic = msg.get("topic")
                    payload = msg.get("payload", {})
                    
                    text = None
                    if topic == "trade_plan_ready":
                        text = f"📈 *JARVIS Trade Plan Ready*:\nSymbol: {payload.get('symbol')}\nScore: {payload.get('setup_score')}\nTrigger Price: {payload.get('trigger_price')}"
                    elif topic == "market_warning":
                        text = f"⚠️ *JARVIS Market Warning*:\nEvent: {payload.get('event')}\nImpact: {payload.get('impact')}\nDetail: {payload.get('title')}"
                    elif topic == "infra_alert":
                        text = f"🔧 *JARVIS Infrastructure Alert*:\nEvent: {payload.get('event')}"
                    
                    if text:
                        new_notifications.append((msg_id, text))
            except Exception:
                continue

    if not new_notifications:
        print("No new notifications to mirror.")
        return

    telegram_cfg = config.get("telegram", {})
    slack_cfg = config.get("slack", {})

    for msg_id, text in new_notifications:
        if args.dry_run:
            print(f"[DRY-RUN] Mirroring notification for {msg_id}:")
            print(text)
            print("-" * 30)
            sent_list.append(msg_id)
        else:
            sent_ok = False
            # Send Telegram
            if telegram_cfg.get("enabled") and telegram_cfg.get("bot_token") and telegram_cfg.get("chat_id"):
                try:
                    send_telegram(telegram_cfg["bot_token"], telegram_cfg["chat_id"], text)
                    sent_ok = True
                except Exception as e:
                    print(f"Failed to send Telegram notification: {e}")
            
            # Send Slack
            if slack_cfg.get("enabled") and slack_cfg.get("webhook_url"):
                try:
                    send_slack(slack_cfg["webhook_url"], text)
                    sent_ok = True
                except Exception as e:
                    print(f"Failed to send Slack notification: {e}")

            # If dry-run is not active, but configs are disabled, we print info
            if not telegram_cfg.get("enabled") and not slack_cfg.get("enabled"):
                print(f"[INFO] Notifications disabled. Mirrored content for {msg_id}:")
                print(text)
                sent_ok = True # mark true so we don't repeat print

            if sent_ok:
                sent_list.append(msg_id)

    save_sent_notifications(sent_list)

if __name__ == "__main__":
    main()
