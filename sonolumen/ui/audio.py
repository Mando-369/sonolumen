"""Hydrophone-trace → audible WAV synthesis. §15.5 "Listen" feature.

The real hydrophone signal sits at 25–40 kHz (above hearing). We
pitch-shift down by `pitch_factor` (default 8×) by resampling at a
lower rate, which both lowers the perceived pitch *and* time-stretches
the trace so the collapse cadence remains audible.

Pure NumPy + stdlib `wave`; no audio library dependency.
"""

from __future__ import annotations

import io
import struct
import wave
from typing import Optional

import numpy as np


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def hydrophone_to_wav(
    t: np.ndarray,
    V: np.ndarray,
    *,
    pitch_factor: float = 8.0,
    target_sample_rate_hz: int = 44_100,
    target_duration_s: Optional[float] = None,
) -> bytes:
    """Render a hydrophone V(t) trace as a WAV byte string.

    Args:
      t: time array (s).
      V: hydrophone voltage trace (arbitrary units; rescaled to ±0.95).
      pitch_factor: divisor applied to the perceived frequency. 8 maps
        a 25 kHz collapse pulse to ~3 kHz (audible squeak).
      target_sample_rate_hz: output WAV sample rate (Hz). 44.1 kHz is
        the common audio default.
      target_duration_s: if provided, time-stretch / pad the output to
        exactly this duration; otherwise the natural length after pitch
        shift (= original_duration · pitch_factor).

    Returns the WAV bytes (16-bit PCM mono).
    """
    if len(t) < 2 or len(V) != len(t):
        return _silent_wav(0.5, target_sample_rate_hz)

    duration = float(t[-1] - t[0])
    if duration <= 0.0:
        return _silent_wav(0.5, target_sample_rate_hz)

    audible_duration = duration * pitch_factor
    if target_duration_s is not None and target_duration_s > 0.0:
        audible_duration = float(target_duration_s)

    n_out = max(int(audible_duration * target_sample_rate_hz), 1)
    # Resample the V(t) trace onto the output time grid:
    # the output sample at index k corresponds to original time
    # `t_orig = (k / pitch_factor) / target_sample_rate_hz`
    out_indices = np.arange(n_out)
    t_orig = (out_indices / pitch_factor) / target_sample_rate_hz
    t_orig = np.clip(t_orig, 0.0, duration)
    samples = np.interp(t_orig, t - t[0], V)

    # Normalise to ±0.95 of int16 range
    peak = float(np.max(np.abs(samples)) or 1.0)
    samples = (samples / peak) * 0.95
    pcm = (samples * 32767).astype(np.int16)

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(target_sample_rate_hz)
        wf.writeframes(pcm.tobytes())
    return buf.getvalue()


def wav_to_data_uri(wav_bytes: bytes) -> str:
    """Convert WAV bytes to a base64 data: URI suitable for an HTML <audio> tag."""
    import base64
    b64 = base64.b64encode(wav_bytes).decode("ascii")
    return f"data:audio/wav;base64,{b64}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _silent_wav(duration_s: float, sample_rate: int) -> bytes:
    """Return a silent mono WAV of `duration_s`."""
    n = int(duration_s * sample_rate)
    pcm = np.zeros(n, dtype=np.int16).tobytes()
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm)
    return buf.getvalue()
