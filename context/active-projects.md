# Active Projects

## JARVIS Platform
*   **Owner:** Jitheesh
*   **Status:** Operational — Voice + Clap + GCP prod + Iron Man HUD v4
*   **Dashboard:** https://storage.googleapis.com/jarvis-jitheesh-2026/dashboard.html
*   **Next Actions:**
    - [x] Voice enrollment + clap trigger
    - [x] Cinematic HUD with live news/weather/markets/devops tabs
    - [x] Keeper agent — personal life, birthdays, multi-channel alerts
    - [ ] Fill family birthdays in `config/personal.yaml`
    - [ ] Enable notifications in `config/notifications.yaml` (Telegram / WhatsApp / Email)
    - [x] Light local mode — GCP handles dashboard/DevOps; Keeper only on laptop

## Keeper Setup (one-time)
1. Edit `config/personal.yaml` — add mother/father/sibling birthdays (MM-DD)
2. Copy `config/notifications.yaml.example` → `config/notifications.yaml`
3. **Telegram:** @BotFather token + chat_id
4. **WhatsApp:** Register at callmebot.com → add apikey (phone: +919846278548)
5. **Email:** Gmail app password in notifications.yaml
6. Run `bash scripts/install_autostart.sh` to enable 07:00 & 20:00 IST scans
