# Task Checklist — JARVIS Platform

## Phases 0–4
- [x] Foundation, Bus, Data pipelines, Voice, Piper TTS, Mirroring

## Phase 5 — Live Context & Console
- [x] build_live_context.py, intent_router.py, jarvis_loop.py
- [x] Live dashboard panels (priorities, markets, projects, warnings)
- [x] launch_jarvis.py smart brief

## Phase 5b — Avengers Voice Activation
- [x] speaker_verify.py + enroll_speaker.py
- [x] wake_word.py (openWakeWord / Porcupine / Whisper / keyboard)
- [x] jarvis_daemon.py always-on loop
- [x] refresh_if_stale.py (6h cache TTL)
- [x] com.jarvis.voice.plist
- [x] test_phase5b.sh validation
- [x] activate_jarvis.sh helper
- [x] Configurable speaker_threshold + wake sensitivity
- [ ] **Manual:** python3 voice/enroll_speaker.py (Jitheesh voiceprint)
- [ ] **Manual:** python3 voice/jarvis_daemon.py --once --no-wake
- [ ] **Manual:** launchctl load com.jarvis.voice.plist (needs Full Disk Access on Desktop)
- [x] validate_voice_hardware.sh — mic, whisper, TTS, intent pipeline
