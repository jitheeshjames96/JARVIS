#!/usr/bin/env python3
import os
import json
import argparse
import shutil

def get_arg_parser():
    parser = argparse.ArgumentParser(description="Poll messages from the JARVIS bus for a specific agent.")
    parser.add_argument("--agent", required=True, help="Agent polling the bus")
    return parser

def main():
    parser = get_arg_parser()
    args = parser.parse_args()

    bus_dir = "cache/bus"
    inbox_dir = os.path.join(bus_dir, "inbox")
    processed_dir = os.path.join(bus_dir, "processed")
    broadcast_dir = os.path.join(bus_dir, "broadcast")

    os.makedirs(inbox_dir, exist_ok=True)
    os.makedirs(processed_dir, exist_ok=True)
    os.makedirs(broadcast_dir, exist_ok=True)

    polled_messages = []

    # 1. Poll inbox (agent-specific targeted messages)
    if os.path.exists(inbox_dir):
        for fname in os.listdir(inbox_dir):
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(inbox_dir, fname)
            try:
                with open(fpath, "r") as f:
                    msg = json.load(f)
                
                if msg.get("to") == args.agent:
                    # Mark status as read
                    msg["status"] = "read"
                    polled_messages.append(msg)
                    
                    # Move to processed
                    processed_path = os.path.join(processed_dir, fname)
                    with open(processed_path, "w") as f:
                        json.dump(msg, f, indent=2)
                    os.remove(fpath)
            except Exception as e:
                print(f"Error reading message {fname}: {e}")

    # 2. Poll broadcasts (one-to-many announcements)
    # Track which broadcasts this agent has already read using a local cache file
    tracking_file = os.path.join(bus_dir, f"read_broadcasts_{args.agent.lower()}.json")
    read_broadcast_ids = []
    if os.path.exists(tracking_file):
        try:
            with open(tracking_file, "r") as f:
                read_broadcast_ids = json.load(f)
        except Exception:
            pass

    new_broadcast_ids = list(read_broadcast_ids)
    if os.path.exists(broadcast_dir):
        for fname in os.listdir(broadcast_dir):
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(broadcast_dir, fname)
            try:
                with open(fpath, "r") as f:
                    msg = json.load(f)
                
                msg_id = msg.get("message_id")
                if msg_id not in read_broadcast_ids:
                    polled_messages.append(msg)
                    new_broadcast_ids.append(msg_id)
            except Exception as e:
                print(f"Error reading broadcast {fname}: {e}")

    # Save tracking file if there are updates
    if len(new_broadcast_ids) > len(read_broadcast_ids):
        try:
            with open(tracking_file, "w") as f:
                json.dump(new_broadcast_ids, f)
        except Exception:
            pass

    # Auto-regenerate HTML dashboard
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        gen_script = os.path.join(script_dir, "generate_dashboard.py")
        if os.path.exists(gen_script):
            import subprocess
            subprocess.run(["python3", gen_script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

    # Output polled messages as JSON array
    print(json.dumps(polled_messages, indent=2))

if __name__ == "__main__":
    main()
