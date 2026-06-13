#!/usr/bin/env python3
"""Keeper agent — personal life, family birthdays, events, and proactive reminders."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "cache" / "keeper-report.json"
SENT = ROOT / "cache" / "keeper-notifications-sent.json"
IST = ZoneInfo("Asia/Kolkata")

sys.path.insert(0, str(ROOT / "scripts"))
from notify_channels import deliver, load_personal  # noqa: E402


def _parse_mmdd(raw: str, year: int) -> date | None:
    raw = (raw or "").strip()
    if not raw:
        return None
    parts = raw.replace("/", "-").split("-")
    try:
        if len(parts) == 2:
            m, d = int(parts[0]), int(parts[1])
            return date(year, m, d)
        if len(parts) == 3:
            y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
            return date(y, m, d)
    except ValueError:
        return None
    return None


def _next_occurrence(mmdd: str, today: date) -> date | None:
    d = _parse_mmdd(mmdd, today.year)
    if not d:
        return None
    if d < today:
        d = _parse_mmdd(mmdd, today.year + 1)
    return d


def _days_until(target: date, today: date) -> int:
    return (target - today).days


def _load_sent() -> set[str]:
    if not SENT.exists():
        return set()
    try:
        with SENT.open(encoding="utf-8") as f:
            return set(json.load(f))
    except (json.JSONDecodeError, OSError):
        return set()


def _save_sent(keys: set[str]) -> None:
    SENT.parent.mkdir(parents=True, exist_ok=True)
    with SENT.open("w", encoding="utf-8") as f:
        json.dump(sorted(keys), f, indent=2)


def _reminder_key(kind: str, label: str, target: date, offset: int) -> str:
    return f"{kind}:{label}:{target.isoformat()}:{offset}d"


def scan(send: bool = True, dry_run: bool = False) -> dict:
    personal = load_personal()
    owner = personal.get("owner", {})
    tz_name = personal.get("reminders", {}).get("timezone", "Asia/Kolkata")
    today = datetime.now(ZoneInfo(tz_name)).date()
    default_days = personal.get("reminders", {}).get("default_remind_days", [7, 1, 0])

    upcoming: list[dict] = []
    due_today: list[dict] = []
    sent_keys = _load_sent()
    new_notifications: list[dict] = []

    def add_item(kind: str, label: str, target: date, relation: str, remind_days: list[int], extra: str = ""):
        days = _days_until(target, today)
        if days < 0:
            return
        entry = {
            "kind": kind,
            "label": label,
            "relation": relation,
            "date": target.isoformat(),
            "days_until": days,
            "display_date": target.strftime("%d %b"),
            "notes": extra,
        }
        upcoming.append(entry)
        if days == 0:
            due_today.append(entry)

        for offset in remind_days:
            if days != offset:
                continue
            key = _reminder_key(kind, label, target, offset)
            if key in sent_keys:
                continue
            when = "today" if offset == 0 else f"in {offset} day{'s' if offset != 1 else ''}"
            msg = (
                f"🗓 JARVIS Keeper\n"
                f"{label} ({relation}) — {when}\n"
                f"Date: {target.strftime('%d %B %Y')}"
            )
            if extra:
                msg += f"\nNote: {extra}"
            new_notifications.append({"key": key, "message": msg, "entry": entry})

    for contact in personal.get("contacts", []):
        bday = contact.get("birthday", "")
        if not bday:
            continue
        target = _next_occurrence(bday, today)
        if not target:
            continue
        remind = contact.get("remind_days") or default_days
        add_item(
            "birthday",
            contact.get("name", "Contact"),
            target,
            contact.get("relation", "family"),
            remind,
            contact.get("notes", ""),
        )

    for event in personal.get("events", []):
        raw_date = event.get("date", "")
        if not raw_date:
            continue
        if event.get("recurring"):
            target = _next_occurrence(raw_date, today)
        else:
            target = _parse_mmdd(raw_date, today.year)
        if not target:
            continue
        remind = event.get("remind_days") or default_days
        add_item(
            "event",
            event.get("title", "Event"),
            target,
            event.get("category", "life"),
            remind,
            event.get("notes", ""),
        )

    for prio in personal.get("life_priorities", []):
        if prio.get("status", "open") == "done":
            continue
        raw_due = prio.get("due", "")
        if not raw_due:
            continue
        target = _parse_mmdd(raw_due, today.year)
        if not target:
            continue
        remind = prio.get("remind_days") or [14, 7, 1]
        add_item(
            "priority",
            prio.get("text", "Priority"),
            target,
            prio.get("category", "personal"),
            remind,
        )

    owner_bday = owner.get("birthday", "")
    if owner_bday:
        target = _next_occurrence(owner_bday, today)
        if target:
            add_item("birthday", owner.get("name", "You"), target, "self", default_days)

    upcoming.sort(key=lambda x: x["days_until"])

    delivery_results = []
    if send and new_notifications:
        for note in new_notifications:
            if dry_run:
                print(f"[DRY-RUN] Would send: {note['message']}")
                sent_keys.add(note["key"])
                continue
            results = deliver(note["message"], subject=f"Keeper: {note['entry']['label']}", dry_run=False)
            if any(v is True for v in results.values()):
                sent_keys.add(note["key"])
                delivery_results.append({"key": note["key"], "channels": results})
                payload = json.dumps({
                    "event": note["entry"]["kind"],
                    "label": note["entry"]["label"],
                    "date": note["entry"]["date"],
                    "days_until": note["entry"]["days_until"],
                    "message": note["message"],
                })
                subprocess.run([
                    "python3", str(ROOT / "scripts" / "bus_write.py"),
                    "--from-agent", "Keeper",
                    "--to-agent", "Synergy",
                    "--topic", "personal_reminder",
                    "--payload", payload,
                    "--priority", "normal",
                ], check=False)

    if send:
        _save_sent(sent_keys)

    incomplete = sum(1 for c in personal.get("contacts", []) if not c.get("birthday"))
    summary = (
        f"{len(due_today)} today, {len(upcoming)} upcoming"
        if upcoming else "Add birthdays in config/personal.yaml"
    )

    report = {
        "agent": "Keeper",
        "checked_at": datetime.now(IST).isoformat(),
        "owner": owner.get("name", "Jitheesh"),
        "phone": owner.get("phone", ""),
        "status": "alert" if due_today else ("running" if upcoming else "idle"),
        "upcoming_count": len(upcoming),
        "due_today": due_today,
        "upcoming": upcoming[:30],
        "notifications_sent": len(delivery_results),
        "contacts_missing_birthdays": incomplete,
        "summary": summary,
    }

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    with REPORT.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
        f.write("\n")

    state = "alert" if due_today else ("running" if upcoming else "idle")
    subprocess.run([
        "python3", str(ROOT / "scripts" / "update_agent_status.py"),
        "--agent", "Keeper",
        "--state", state,
        "--summary", summary,
        "--next-run", "07:00 & 20:00 IST",
    ], check=False)

    return report


def main() -> int:
    import argparse
    p = argparse.ArgumentParser(description="Keeper personal reminders agent")
    p.add_argument("--dry-run", action="store_true", help="Preview without sending")
    p.add_argument("--no-send", action="store_true", help="Scan only, no notifications")
    args = p.parse_args()
    report = scan(send=not args.no_send, dry_run=args.dry_run)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
