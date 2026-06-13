#!/usr/bin/env python3
import os
import json
import argparse
from datetime import datetime

def get_arg_parser():
    parser = argparse.ArgumentParser(description="Log an agent action to the audit trail.")
    parser.add_argument("--agent", required=True, help="Agent performing action")
    parser.add_argument("--action", required=True, help="Action description")
    parser.add_argument("--message-id", default=None, help="Associated bus message ID")
    parser.add_argument("--approved-by", default="Auto", help="Approval status (e.g. User, Auto)")
    return parser

def main():
    parser = get_arg_parser()
    args = parser.parse_args()

    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "agent-actions.jsonl")

    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "agent": args.agent,
        "action": args.action,
        "message_id": args.message_id,
        "approved_by": args.approved_by
    }

    with open(log_file, "a") as f:
        f.write(json.dumps(log_entry) + "\n")

    print(f"Action logged for {args.agent}: {args.action}")

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
