# Keeper — Personal Life & Family Manager

## Scope
Manages Jitheesh's personal details, relatives, sibling birthdays, important life events, and personal priorities. Proactively notifies via WhatsApp, Telegram, or email before key dates.

## Data Files
* `config/personal.yaml` — owner profile, contacts, events, life priorities (gitignored)
* `config/personal.yaml.example` — template structure
* `cache/keeper-report.json` — latest scan results for HUD and voice

## Notification Channels
Configured in `config/notifications.yaml`:
* **Telegram** — BotFather token + chat_id
* **WhatsApp** — CallMeBot API (register at callmebot.com, add apikey)
* **Email** — Gmail SMTP with app password

Owner phone default: `+919846278548`

## Workflow
```
Load personal.yaml → Scan birthdays/events/priorities → Match remind_days →
Deliver via notify_channels → Write bus personal_reminder → Update agent status
```

## Bus Integration
* **Writes:** `personal_reminder` (to Synergy) when a notification fires
* **Reads:** none required

## Scripts
```bash
python3 scripts/keeper_reminders.py           # scan + notify
python3 scripts/keeper_reminders.py --dry-run # preview
python3 scripts/notify_channels.py "test"     # test channels
```

## Schedule
`com.jarvis.keeper` launchd — 07:00 and 20:00 IST daily

## Voice Commands
* "Personal reminders" / "Family birthdays" / "What's coming up"
* "Open personal tab" on dashboard
