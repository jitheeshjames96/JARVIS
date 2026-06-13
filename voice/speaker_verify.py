#!/usr/bin/env python3
"""Speaker embedding extraction and verification for JARVIS."""

from __future__ import annotations

import json
import wave
from pathlib import Path
from typing import Optional

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
PROFILE_PATH = ROOT / "cache" / "voice-profile.json"
DEFAULT_THRESHOLD = 0.72


def load_wav(path: str) -> tuple[np.ndarray, int]:
    with wave.open(path, "rb") as wf:
        sr = wf.getframerate()
        n = wf.getnframes()
        raw = wf.readframes(n)
        audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        if wf.getnchannels() > 1:
            audio = audio.reshape(-1, wf.getnchannels()).mean(axis=1)
    return audio, sr


def _simple_embed(audio: np.ndarray, sr: int) -> np.ndarray:
    """Lightweight spectral embedding (no torch)."""
    if len(audio) < sr // 4:
        return np.zeros(32)
    # Normalize
    audio = audio - np.mean(audio)
    peak = np.max(np.abs(audio)) or 1.0
    audio = audio / peak
    # Frame FFT features
    frame = int(sr * 0.025)
    hop = int(sr * 0.010)
    feats = []
    for start in range(0, len(audio) - frame, hop):
        chunk = audio[start : start + frame] * np.hanning(frame)
        spec = np.abs(np.fft.rfft(chunk))
        # Mel-like bins
        bins = np.array_split(spec, 32)
        feats.append([b.mean() for b in bins])
    mat = np.array(feats)
    emb = mat.mean(axis=0)
    emb = emb / (np.linalg.norm(emb) + 1e-9)
    return emb


def _resemblyzer_embed(path: str) -> Optional[np.ndarray]:
    try:
        from resemblyzer import VoiceEncoder, preprocess_wav  # type: ignore
        encoder = VoiceEncoder()
        wav = preprocess_wav(path)
        emb = encoder.embed_utterance(wav)
        return emb / (np.linalg.norm(emb) + 1e-9)
    except Exception:
        return None


def compute_embedding(wav_path: str) -> list[float]:
    rs = _resemblyzer_embed(wav_path)
    if rs is not None:
        return rs.tolist()
    audio, sr = load_wav(wav_path)
    return _simple_embed(audio, sr).tolist()


def cosine_similarity(a: list[float], b: list[float]) -> float:
    va = np.array(a, dtype=np.float32)
    vb = np.array(b, dtype=np.float32)
    return float(np.dot(va, vb) / (np.linalg.norm(va) * np.linalg.norm(vb) + 1e-9))


def load_profile() -> dict | None:
    if not PROFILE_PATH.exists():
        return None
    try:
        with PROFILE_PATH.open(encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def profile_enrolled() -> bool:
    p = load_profile()
    return bool(p and p.get("embedding"))


def verify(wav_path: str, threshold: float | None = None) -> tuple[bool, float]:
    """
    Return (accepted, score).
    If no profile enrolled, accept with score 1.0 (open mode).
    """
    if threshold is None:
        try:
            from daemon_config import speaker_threshold
            threshold = speaker_threshold()
        except Exception:
            threshold = DEFAULT_THRESHOLD
        profile = load_profile()
        if profile and profile.get("threshold"):
            threshold = float(profile["threshold"])

    profile = load_profile()
    if not profile or not profile.get("embedding"):
        return True, 1.0

    probe = compute_embedding(wav_path)
    ref = profile["embedding"]
    score = cosine_similarity(probe, ref)
    return score >= threshold, score


def build_profile_from_samples(wav_paths: list[str]) -> list[float]:
    embeddings = [compute_embedding(p) for p in wav_paths if Path(p).exists()]
    if not embeddings:
        raise ValueError("No valid enrollment samples")
    mat = np.array(embeddings)
    mean = mat.mean(axis=0)
    mean = mean / (np.linalg.norm(mean) + 1e-9)
    return mean.tolist()
