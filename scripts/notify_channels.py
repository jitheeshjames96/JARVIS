#!/usr/bin/env python3
"""Unified notification delivery — Telegram, WhatsApp, Email."""

from __future__ import annotations

import json
import smtplib
import ssl
import urllib.parse
import urllib.request
from email.mime.text import MIMEText
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_config() -> dict:
    import yaml
    for name in ("notifications.yaml", "notifications.yaml.example"):
        path = ROOT / "config" / name
        if path.exists():
            with path.open(encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
    return {}


def load_personal() -> dict:
    import yaml
    for name in ("personal.yaml", "personal.yaml.example"):
        path = ROOT / "config" / name
        if path.exists():
            with path.open(encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                if name.endswith(".example") and path.name == "personal.yaml.example":
                    # Only use example if personal.yaml missing
                    personal = ROOT / "config" / "personal.yaml"
                    if personal.exists():
                        continue
                return data
    return {}


def send_telegram(token: str, chat_id: str, text: str) -> bool:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
    }).encode("utf-8")
    req = urllib.request.Request(url, data=data)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.status == 200


def send_whatsapp_callmebot(phone: str, apikey: str, text: str) -> bool:
    """CallMeBot free WhatsApp API — user must register at callmebot.com first."""
    params = urllib.parse.urlencode({
        "phone": phone,
        "text": text,
        "apikey": apikey,
    })
    url = f"https://api.callmebot.com/whatsapp.php?{params}"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=20) as resp:
        body = resp.read().decode("utf-8", errors="replace")
        return "OK" in body.upper() or resp.status == 200


def send_email(cfg: dict, text: str, subject: str = "JARVIS Keeper Reminder") -> bool:
    host = cfg.get("smtp_host", "smtp.gmail.com")
    port = int(cfg.get("smtp_port", 587))
    user = cfg.get("username", "")
    password = cfg.get("password", "")
    to_addr = cfg.get("to") or user
    if not user or not password or not to_addr:
        return False
    msg = MIMEText(text, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to_addr
    ctx = ssl.create_default_context()
    with smtplib.SMTP(host, port, timeout=20) as server:
        server.starttls(context=ctx)
        server.login(user, password)
        server.sendmail(user, [to_addr], msg.as_string())
    return True


def deliver(text: str, subject: str = "JARVIS Keeper Reminder", dry_run: bool = False) -> dict:
    """Send to all enabled channels. Returns {channel: ok} map."""
    cfg = load_config()
    personal = load_personal()
    owner = personal.get("owner", {})
    results: dict[str, bool | str] = {}

    if dry_run:
        print(f"[DRY-RUN] {subject}\n{text}")
        return {"dry_run": True}

    tg = cfg.get("telegram", {})
    if tg.get("enabled") and tg.get("bot_token") and tg.get("chat_id"):
        try:
            results["telegram"] = send_telegram(tg["bot_token"], tg["chat_id"], text)
        except Exception as exc:
            results["telegram"] = str(exc)

    wa = cfg.get("whatsapp", {})
    phone = wa.get("phone") or owner.get("phone", "")
    apikey = wa.get("apikey", "")
    if wa.get("enabled") and phone and apikey:
        try:
            results["whatsapp"] = send_whatsapp_callmebot(phone, apikey, text)
        except Exception as exc:
            results["whatsapp"] = str(exc)

    em = cfg.get("email", {})
    to_email = em.get("to") or owner.get("email", "")
    if em.get("enabled"):
        em = {**em, "to": to_email}
        try:
            results["email"] = send_email(em, text, subject=subject)
        except Exception as exc:
            results["email"] = str(exc)

    return results


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("message", nargs="?", default="JARVIS notification test.")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    out = deliver(args.message, dry_run=args.dry_run)
    print(json.dumps(out, indent=2))
