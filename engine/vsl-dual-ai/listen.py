"""Cheap "what did the room just hear" analysis, for the models' brief.

The duo needs a shared ear: if the piano is already loud, the other model
should thin out. Capture the *sampler output* (WASAPI loopback or a virtual
cable) and reduce 1 bar to a few numbers. Everything degrades quietly: with no
sounddevice / no numpy the report is simply "unavailable" and the music plays
on.

    python listen.py --probe            # list input devices
    python listen.py --device 3 --secs 5
"""
from __future__ import annotations

import argparse
import math
import threading
import time

try:                                   # optional, never required
    import numpy as np
except Exception:                      # pragma: no cover
    np = None


class Ear:
    """Background listener: keeps the last report string ready."""

    def __init__(self, device: int | None = None, sr: int = 48000, block: int = 1024) -> None:
        self.report = "unavailable"
        self.ok = False
        self._stop = False
        self._buf: list[float] = []
        self._thread: threading.Thread | None = None
        self.device = device
        self.sr = sr
        self.block = block

    # -- lifecycle ---------------------------------------------------------
    def start(self) -> "Ear":
        if np is None:
            return self
        try:
            import sounddevice as sd
        except Exception:
            return self
        try:
            stream = sd.InputStream(device=self.device, channels=2,
                                    samplerate=self.sr, blocksize=self.block)
            stream.start()
        except Exception as exc:
            print(f"[listen] no capture: {exc}")
            return self

        self.ok = True
        self._stream = stream

        def loop() -> None:
            while not self._stop:
                try:
                    data, _ = stream.read(self.block)
                except Exception:
                    break
                mono = data.mean(axis=1) if getattr(data, "ndim", 1) > 1 else data
                self._buf.extend(mono.tolist())
                if len(self._buf) > self.sr:          # keep ~1 s
                    self._buf = self._buf[-self.sr:]
                self.report = self._analyse(mono)

        self._thread = threading.Thread(target=loop, daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        self._stop = True
        try:
            self._stream.stop()
        except Exception:
            pass

    # -- analysis ----------------------------------------------------------
    def _analyse(self, block) -> str:
        rms = float(np.sqrt(np.mean(np.square(block)))) if len(block) else 0.0
        db = 20 * math.log10(max(rms, 1e-6))
        spec = np.abs(np.fft.rfft(block * np.hanning(len(block))))
        freqs = np.fft.rfftfreq(len(block), 1 / self.sr)
        if spec.sum() <= 1e-9:
            return "silence"
        centroid = float((spec * freqs).sum() / spec.sum())
        peak = float(freqs[int(spec.argmax())])
        # onset density: rising edges above the local mean energy
        energy = np.abs(block)
        mean = energy.mean() + 1e-9
        onsets = int(np.sum((energy[1:-1] > 2.2 * mean) &
                            (energy[1:-1] > energy[:-2]) &
                            (energy[1:-1] > energy[2:])))
        density = onsets / (len(block) / self.sr)
        level = "quiet" if db < -40 else "soft" if db < -26 else \
                "moderate" if db < -16 else "loud"
        tone = "dark" if centroid < 700 else "warm" if centroid < 1800 else \
               "bright" if centroid < 4000 else "brittle"
        return (f"{level} ({db:.0f} dB), {tone} (centroid {centroid/1000:.1f} kHz, "
                f"peak {peak:.0f} Hz), onsets {density:.1f}/s")

    # -- one-shot ----------------------------------------------------------
    def peek(self) -> str:
        return self.report


def probe() -> None:
    try:
        import sounddevice as sd
    except Exception as exc:
        print(f"sounddevice not available: {exc}")
        return
    for i, d in enumerate(sd.query_devices()):
        if d["max_input_channels"] > 0:
            print(f"{i:2d}  {d['name'][:52]:52s}  in={d['max_input_channels']}  "
                  f"sr={int(d['default_samplerate'])}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--device", type=int, default=None)
    ap.add_argument("--secs", type=float, default=5.0)
    a = ap.parse_args()
    if a.probe:
        probe()
    else:
        ear = Ear(a.device).start()
        t_end = time.time() + a.secs
        while time.time() < t_end:
            print("\r" + ear.peek().ljust(90), end="", flush=True)
            time.sleep(0.25)
        ear.stop()
        print()
