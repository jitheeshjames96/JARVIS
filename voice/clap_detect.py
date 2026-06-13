#!/usr/bin/env python3
"""Clap-trigger for JARVIS — listen for a sharp clap to activate."""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "voice"))


def _clap_config() -> dict:
    try:
        from daemon_config import load_daemon_config
        cfg = load_daemon_config()
    except Exception:
        cfg = {}
    return {
        "mode": cfg.get("clap_mode", "single"),
        "threshold": float(cfg.get("clap_threshold", 0.12)),
        "spike_ratio": float(cfg.get("clap_spike_ratio", 2.8)),
        "cooldown_s": float(cfg.get("clap_cooldown_s", 1.2)),
        "double_window_ms": int(cfg.get("clap_double_window_ms", 500)),
    }


def _chunk_score(audio) -> tuple[float, float]:
    """Return (peak_amplitude, rms) for clap detection."""
    import numpy as np  # type: ignore
    peak = float(np.max(np.abs(audio)))
    rms = float(np.sqrt(np.mean(audio * audio)))
    return peak, rms


def wait_for_clap(timeout: float | None = None) -> bool:
    """Block until clap detected. Returns True on trigger, False on timeout/exit."""
    try:
        import numpy as np  # type: ignore
        import pyaudio  # type: ignore
    except ImportError:
        print("[clap] Install: pip3 install pyaudio numpy")
        return False

    cfg = _clap_config()
    chunk = 512  # smaller chunk = faster transient response
    rate = 16000
    mode = cfg["mode"]
    abs_threshold = cfg["threshold"]
    spike_ratio = cfg["spike_ratio"]
    cooldown = cfg["cooldown_s"]
    double_window = cfg["double_window_ms"] / 1000.0

    pa = pyaudio.PyAudio()
    stream = pa.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=rate,
        input=True,
        frames_per_buffer=chunk,
    )

    print(f"[clap] Listening for {mode} clap (threshold={abs_threshold})... Ctrl+C to stop")
    baseline: list[float] = []
    clap_times: list[float] = []
    last_trigger = 0.0
    start = time.time()

    try:
        while True:
            if timeout and (time.time() - start) > timeout:
                return False

            raw = stream.read(chunk, exception_on_overflow=False)
            audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
            peak, rms = _chunk_score(audio)
            # Claps are sharp transients — weight peak higher than RMS
            score = max(peak, rms * 1.8)

            baseline.append(score)
            if len(baseline) > 50:
                baseline.pop(0)

            if len(baseline) < 15:
                continue

            floor = float(np.median(baseline)) + 0.004
            dynamic_threshold = max(abs_threshold, floor * spike_ratio)

            if score >= dynamic_threshold:
                now = time.time()
                if clap_times and (now - clap_times[-1]) < 0.06:
                    continue
                if (now - last_trigger) < cooldown:
                    continue

                clap_times.append(now)
                clap_times = [t for t in clap_times if now - t < 1.0]

                if mode == "double":
                    if len(clap_times) >= 2 and (clap_times[-1] - clap_times[-2]) <= double_window:
                        print(f"[clap] Double clap (score={score:.3f})")
                        return True
                else:
                    print(f"[clap] Clap detected (score={score:.3f}, threshold={dynamic_threshold:.3f})")
                    return True
    except KeyboardInterrupt:
        return False
    finally:
        stream.stop_stream()
        stream.close()
        pa.terminate()


def calibrate(seconds: int = 8) -> None:
    """Print live levels — clap during window to tune threshold."""
    try:
        import numpy as np  # type: ignore
        import pyaudio  # type: ignore
    except ImportError:
        print("Install: pip3 install pyaudio numpy")
        return

    chunk = 512
    rate = 16000
    pa = pyaudio.PyAudio()
    stream = pa.open(
        format=pyaudio.paInt16, channels=1, rate=rate,
        input=True, frames_per_buffer=chunk,
    )
    print(f"=== Clap calibration ({seconds}s) ===")
    print("Stay quiet, then clap. Watch SCORE peak.\n")
    start = time.time()
    peak_score = 0.0
    try:
        while time.time() - start < seconds:
            raw = stream.read(chunk, exception_on_overflow=False)
            audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
            pk, rms = _chunk_score(audio)
            score = max(pk, rms * 1.8)
            peak_score = max(peak_score, score)
            bar = "#" * min(50, int(score * 100))
            print(f"\rscore {score:.3f}  peak {peak_score:.3f}  {bar:<50}", end="", flush=True)
        suggested = max(0.08, round(peak_score * 0.55, 2))
        print(f"\n\nSet in config/profile.yaml:")
        print(f"  clap_threshold: {suggested}")
    finally:
        stream.stop_stream()
        stream.close()
        pa.terminate()


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--calibrate", action="store_true")
    p.add_argument("--test", action="store_true", help="Wait for one clap then exit")
    args = p.parse_args()
    if args.calibrate:
        calibrate()
    elif args.test:
        ok = wait_for_clap()
        print("triggered" if ok else "no clap")
    else:
        calibrate()
