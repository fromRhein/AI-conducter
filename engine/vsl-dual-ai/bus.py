"""Clock, event scheduler, phrase validation and the parameter (CC) registry.

The scheduler is the only thing that touches MIDI. It runs on a monotonic
perf_counter() clock with a 1.5 ms spin window, so note timing does not depend
on how fast a model answered. That separation is the whole trick: models plan
ahead, the bus renders exactly on time.
"""
from __future__ import annotations

import heapq
import itertools
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Iterable

# ---------------------------------------------------------------- clock ----


class Clock:
    """Tempo map: beats -> seconds. One tempo for now, ready for a list."""

    def __init__(self, bpm: float, beats_per_bar: int = 4) -> None:
        self.bpm = float(bpm)
        self.beats_per_bar = beats_per_bar

    @property
    def sec_per_beat(self) -> float:
        return 60.0 / self.bpm

    @property
    def bar_sec(self) -> float:
        return self.sec_per_beat * self.beats_per_bar

    def bar_start(self, t0: float, bar: int) -> float:
        return t0 + bar * self.bar_sec

    def beat_of(self, t0: float, t: float) -> float:
        return (t - t0) / self.sec_per_beat


# ------------------------------------------------------------ scheduler ----


class Scheduler:
    """Absolute-time event scheduler. submit(t_abs, fn) is thread-safe."""

    SPIN = 0.0015

    def __init__(self) -> None:
        self._heap: list[tuple[float, int, Callable[[], None]]] = []
        self._seq = itertools.count()
        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._stop = False
        self.late_total = 0.0
        self.late_max = 0.0
        self.sent = 0
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def submit(self, t_abs: float, fn: Callable[[], None]) -> None:
        with self._lock:
            heapq.heappush(self._heap, (t_abs, next(self._seq), fn))
        self._wake.set()

    def _run(self) -> None:
        while not self._stop:
            with self._lock:
                if not self._heap:
                    nxt = None
                else:
                    nxt = self._heap[0]
            if nxt is None:
                self._wake.wait(0.2)
                self._wake.clear()
                continue
            t, _, fn = nxt
            now = time.perf_counter()
            if now < t - self.SPIN:
                time.sleep(min(t - now - self.SPIN, 0.05))
                continue
            while time.perf_counter() < t:      # spin the last millisecond
                pass
            with self._lock:
                if not self._heap or self._heap[0][0] != t:
                    continue
                heapq.heappop(self._heap)
            late = time.perf_counter() - t
            self.late_total += late
            self.late_max = max(self.late_max, late)
            self.sent += 1
            try:
                fn()
            except Exception as exc:            # never kill the clock thread
                print(f"[scheduler] event failed: {exc}")

    def stop(self) -> None:
        self._stop = True
        self._wake.set()

    def stats(self) -> dict:
        n = max(self.sent, 1)
        return {
            "events": self.sent,
            "late_avg_ms": round(self.late_total / n * 1000, 2),
            "late_max_ms": round(self.late_max * 1000, 2),
        }


# --------------------------------------------------------------- params ----


@dataclass
class Param:
    name: str
    cc: int
    lo: float = 0.0
    hi: float = 1.0
    owner: str = "any"          # "A" | "B" | "any"
    rate_ms: int = 80           # minimum spacing between two CC sends
    ramp_ms: int = 120          # smoothing ramp, kills zipper noise
    _last: float = field(default=0.0, repr=False)


class ParamRegistry:
    """name -> CC, with ownership, rate limiting and smoothing.

    Values arrive as normalised floats 0..1 and leave as 7-bit CC.
    """

    def __init__(self, table: dict, send_cc: Callable[[int, int, int], None]) -> None:
        self._p: dict[str, Param] = {}
        self._send = send_cc
        for name, spec in table.items():
            self._p[name] = Param(
                name=name,
                cc=int(spec["cc"]),
                lo=float(spec.get("lo", 0.0)),
                hi=float(spec.get("hi", 1.0)),
                owner=str(spec.get("owner", "any")),
                rate_ms=int(spec.get("rate_ms", 80)),
                ramp_ms=int(spec.get("ramp_ms", 120)),
            )
        self._lock = threading.Lock()
        self.rejected: list[str] = []

    def names(self) -> list[str]:
        return sorted(self._p)

    def apply(self, name: str, norm: float, ch: int, who: str = "A") -> bool:
        p = self._p.get(name)
        if p is None:
            self.rejected.append(f"{who}:{name}:unknown")
            return False
        if p.owner not in ("any", who):
            self.rejected.append(f"{who}:{name}:owned-by-{p.owner}")
            return False
        now = time.perf_counter()
        if (now - p._last) * 1000 < p.rate_ms:
            self.rejected.append(f"{who}:{name}:rate")
            return False
        p._last = now
        v = max(0.0, min(1.0, float(norm)))
        target = round(p.lo + (p.hi - p.lo) * v)
        target = max(0, min(127, target))
        self._ramp(ch, p, target)
        return True

    def _ramp(self, ch: int, p: Param, target: int) -> None:
        # small stepped ramp so plugin knobs do not jump (zipper noise)
        steps = max(1, p.ramp_ms // 20)
        cur = getattr(p, "_cur", None)
        if cur is None or abs(cur - target) <= 1:
            setattr(p, "_cur", target)
            self._send(ch, p.cc, target)
            return
        delta = (target - cur) / steps
        for i in range(1, steps + 1):
            val = max(0, min(127, round(cur + delta * i)))
            delay = i * 0.02
            threading.Timer(delay, self._send, args=(ch, p.cc, val)).start()
        setattr(p, "_cur", target)


# ----------------------------------------------------------- validation ----


@dataclass
class Note:
    beat: float
    note: int
    vel: int
    dur: float
    ch: int


def validate_phrase(raw: dict, who: str, ch: int, beats_per_bar: int,
                    lo_note: int = 21, hi_note: int = 108,
                    max_notes: int = 96) -> tuple[list[Note], dict, list[str]]:
    """Turn a model reply into safe note events + parameter moves.

    Returns (notes, params, complaints). Anything out of range is dropped,
    never clamped silently into nonsense.
    """
    notes: list[Note] = []
    params: dict[str, float] = {}
    bad: list[str] = []

    for i, ev in enumerate(raw.get("notes", [])[:max_notes]):
        try:
            beat = float(ev["beat"])
            note = int(ev["note"])
            vel = int(ev.get("vel", 80))
            dur = float(ev.get("dur", 0.5))
        except Exception:
            bad.append(f"note[{i}] malformed")
            continue
        if not (0 <= beat < beats_per_bar):
            bad.append(f"note[{i}] beat {beat} out of bar")
            continue
        if not (lo_note <= note <= hi_note):
            bad.append(f"note[{i}] pitch {note} outside role range")
            continue
        if not (0 < dur <= beats_per_bar):
            bad.append(f"note[{i}] dur {dur} invalid")
            continue
        notes.append(Note(beat, note, max(1, min(127, vel)), dur, ch))

    for name, val in (raw.get("params") or {}).items():
        try:
            params[str(name)] = max(0.0, min(1.0, float(val)))
        except Exception:
            bad.append(f"param {name} not numeric")

    notes.sort(key=lambda n: n.beat)
    return notes, params, bad


def sec(beat: float, clock: Clock) -> float:
    return beat * clock.sec_per_beat
