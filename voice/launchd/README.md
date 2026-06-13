# launchd Scheduling & Voice Daemon

`launchd` runs on your Mac local clock. Set timezone to `Asia/Kolkata` for IST schedules.

## Scheduled jobs

| Plist | Schedule | Action |
|-------|----------|--------|
| `com.jarvis.morning.plist` | 07:00 daily | Morning brief + voice |
| `com.jarvis.premarket.plist` | 08:45 daily | Pre-market scan |
| `com.jarvis.eod.plist` | 15:45 daily | EOD swing/penny scan |
| `com.jarvis.voice.plist` | Always on | Voice daemon (wake word) |
| `com.jarvis.wakeword.plist` | Always on | Legacy wake stub |

## Install all agents

```bash
cd voice/launchd
cp *.plist ~/Library/LaunchAgents/

launchctl load ~/Library/LaunchAgents/com.jarvis.morning.plist
launchctl load ~/Library/LaunchAgents/com.jarvis.premarket.plist
launchctl load ~/Library/LaunchAgents/com.jarvis.eod.plist
launchctl load ~/Library/LaunchAgents/com.jarvis.voice.plist

launchctl list | grep jarvis
```

## Voice daemon setup (Phase 5b)

```bash
brew install ffmpeg portaudio
pip3 install faster-whisper openwakeword pyaudio
# Optional: pip3 install pvporcupine pvrecorder resemblyzer
# Optional: export PICOVOICE_ACCESS_KEY=your_key

python3 voice/enroll_speaker.py      # enroll YOUR voice only
python3 voice/jarvis_daemon.py       # foreground test
bash scripts/test_phase5b.sh         # automated checks
bash scripts/validate_voice_hardware.sh  # mic + whisper + TTS pipeline
```

### Cinema mode on Desktop (macOS TCC)

If the repo lives under `~/Desktop`, launchd may fail with `Operation not permitted`.
Grant **Full Disk Access** to Terminal (or `/usr/bin/python3`) in
**System Settings → Privacy & Security → Full Disk Access**, then:

```bash
mkdir -p ~/Library/LaunchAgents
cp voice/launchd/com.jarvis.voice.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.jarvis.voice.plist
```

Alternative: move JARVIS to `~/Projects/JARVIS` (outside protected folders).

## Unload

```bash
launchctl unload ~/Library/LaunchAgents/com.jarvis.voice.plist
```

Logs: `logs/jarvis_daemon_stdout.log`, `logs/jarvis_daemon_stderr.log`
