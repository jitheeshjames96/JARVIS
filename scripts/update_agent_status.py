#!/usr/bin/env python3
import os
import json
import argparse
from datetime import datetime

def get_arg_parser():
    parser = argparse.ArgumentParser(description="Update status of an agent on the status board.")
    parser.add_argument("--agent", required=True, help="Name of the agent (e.g. Sentinel, Oracle)")
    parser.add_argument("--state", required=True, choices=["idle", "running", "alert"], help="Current state of the agent")
    parser.add_argument("--summary", required=True, help="Short text summary of the status")
    parser.add_argument("--next-run", default=None, help="Scheduled next execution time")
    return parser

def main():
    parser = get_arg_parser()
    args = parser.parse_args()

    status_file = "cache/agent-status.json"
    os.makedirs(os.path.dirname(status_file), exist_ok=True)

    status_data = {
        "updated_at": "",
        "agents": {}
    }

    if os.path.exists(status_file):
        try:
            with open(status_file, "r") as f:
                data = json.load(f)
                if "agents" in data:
                    status_data = data
        except Exception:
            pass

    status_data["updated_at"] = datetime.now().isoformat()
    status_data["agents"][args.agent] = {
        "state": args.state,
        "last_run": datetime.now().isoformat(),
        "summary": args.summary,
        "next_run": args.next_run
    }

    # Write atomically
    temp_file = status_file + ".tmp"
    with open(temp_file, "w") as f:
        json.dump(status_data, f, indent=2)
    os.replace(temp_file, status_file)

    print(f"Status board updated for {args.agent}: state={args.state}")

    # Auto-regenerate HTML dashboard
    try:
        import subprocess
        script_dir = os.path.dirname(os.path.abspath(__file__))
        gen_script = os.path.join(script_dir, "generate_dashboard.py")
        if os.path.exists(gen_script):
            subprocess.run(["python3", gen_script], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"Warning: Failed to auto-generate dashboard: {e}")

if __name__ == "__main__":
    main()
