#!/usr/bin/env python3
import os
import json
import uuid
import argparse
from datetime import datetime, timedelta

def get_arg_parser():
    parser = argparse.ArgumentParser(description="Write a message envelope to the JARVIS bus.")
    parser.add_argument("--from-agent", required=True, help="Sending agent name")
    parser.add_argument("--to-agent", required=True, help="Receiving agent name or 'broadcast'")
    parser.add_argument("--topic", required=True, help="Message topic")
    parser.add_argument("--payload", required=True, help="JSON string representing message payload")
    parser.add_argument("--priority", default="normal", choices=["normal", "high"], help="Message priority")
    parser.add_argument("--ttl-hours", type=int, default=4, help="Time to live in hours")
    return parser

def main():
    parser = get_arg_parser()
    args = parser.parse_args()

    try:
        payload_data = json.loads(args.payload)
    except json.JSONDecodeError:
        print("Error: Payload must be a valid JSON string.")
        return

    bus_dir = "cache/bus"
    inbox_dir = os.path.join(bus_dir, "inbox")
    processed_dir = os.path.join(bus_dir, "processed")
    broadcast_dir = os.path.join(bus_dir, "broadcast")

    os.makedirs(inbox_dir, exist_ok=True)
    os.makedirs(processed_dir, exist_ok=True)
    os.makedirs(broadcast_dir, exist_ok=True)

    # 1. Deduplication Rule
    # Check if a message with same "to", "topic", and payload "symbol" was written in last 4 hours
    symbol = payload_data.get("symbol")
    if symbol:
        now = datetime.now()
        dup_found = False
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
                    
                    msg_time = datetime.fromisoformat(msg.get("timestamp"))
                    if msg_time.tzinfo is not None:
                        msg_time = msg_time.astimezone().replace(tzinfo=None)
                    if now - msg_time < timedelta(hours=4):
                        # check topic, receiver, and symbol
                        if (msg.get("topic") == args.topic and 
                            msg.get("to") == args.to_agent and 
                            msg.get("payload", {}).get("symbol") == symbol):
                            dup_found = True
                            break
                except Exception:
                    continue
            if dup_found:
                break
        
        if dup_found:
            print(f"Deduplication triggered: Skip writing duplicate '{args.topic}' for symbol '{symbol}'")
            return

    # 2. Inbox Capacity Cap
    # Max 50 files in inbox; remove oldest if cap exceeded
    if os.path.exists(inbox_dir):
        inbox_files = [os.path.join(inbox_dir, f) for f in os.listdir(inbox_dir) if f.endswith(".json")]
        if len(inbox_files) >= 50:
            inbox_files.sort(key=os.path.getmtime)
            # Remove oldest files to make room
            to_remove = len(inbox_files) - 49
            for i in range(to_remove):
                try:
                    os.remove(inbox_files[i])
                except Exception:
                    pass

    # 3. Create envelope
    message_id = f"msg-{uuid.uuid4()}"
    envelope = {
        "message_id": message_id,
        "timestamp": datetime.now().isoformat(),
        "from": args.from_agent,
        "to": args.to_agent,
        "topic": args.topic,
        "priority": args.priority,
        "ttl_hours": args.ttl_hours,
        "payload": payload_data,
        "status": "unread"
    }

    # If it's a broadcast, save to broadcast/ else inbox/
    target_dir = broadcast_dir if args.to_agent.lower() == "broadcast" else inbox_dir
    target_path = os.path.join(target_dir, f"{message_id}.json")

    with open(target_path, "w") as f:
        json.dump(envelope, f, indent=2)

    print(f"Message written to {target_dir}/{message_id}.json")

    # Auto-regenerate HTML dashboard
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        gen_script = os.path.join(script_dir, "generate_dashboard.py")
        if os.path.exists(gen_script):
            import subprocess
            subprocess.run(["python3", gen_script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

if __name__ == "__main__":
    main()
