# Active Projects

## JARVIS Platform
*   **Owner:** Jitheesh
*   **Status:** Operational — Phases 0–5b complete; GCP prod Sentinel live
*   **Description:** Local agent-oriented chief-of-staff with bus, trading pipelines, voice daemon, and visual console.
*   **GCP Prod:** `jarvis-jitheesh-2026` on `jitheeshjames27@gmail.com` — Sentinel hourly monitor
*   **Next Actions:**
    - [x] Phase 0–5b implementation and validation
    - [x] GitHub push + GCS dashboard hosting (prod)
    - [x] Sentinel GCP agent deployed (Cloud Function + hourly scheduler)
    - [ ] Run `python3 voice/enroll_speaker.py` — voice security lock
    - [ ] Load `com.jarvis.voice.plist` for always-on mode
    - [ ] Enable Telegram in `config/notifications.yaml` (optional)
