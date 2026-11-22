"""Coupled control: what two players actually do to each other, at 100 Hz.

A model cannot answer in 20 ms, and it should not have to. The fast layer is
arithmetic: a phase-locked loop on the partner's onsets, a dynamics balance
loop, and a pedal watch that reacts to density and level. The models write the
*plan*; this file is the reflex.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field


# --------------------------------------------------------------------- PLL

@dataclass
class PLL:
    """Mutual entrainment. Phase error is measured, never assumed.

    e > 0 means the partner is ahead of us, so we speed up: exactly what a duo
    does without a conductor. Gains are per second of phase error, so a 10 ms
    lag asks for about 0.8 % more tempo.
    """

    kp: float = 0.8
    ki: float = 0.30
    clamp: float = 0.045          # tempo authority, +-4.5 %
    offset_clamp: float = 0.022   # per-note timing authority, +-22 ms
    tau: float = 0.10             # smoothing time constant, seconds
    dead: float = 0.002           # deadband: below 2 ms nobody bothers
    windup_guard: float = 0.020   # integrate only while already close
    integral: float = 0.0
    _corr: float = 0.0
    last_error: float = 0.0
    samples: int = 0
    error_abs_sum: float = 0.0

    def observe(self, error_s: float, dt: float) -> None:
        self.last_error = error_s
        self.samples += 1
        self.error_abs_sum += abs(error_s)
        e = 0.0 if abs(error_s) < self.dead else error_s
        if abs(error_s) <= self.windup_guard:
            self.integral = max(-0.25, min(0.25, self.integral + e * dt))
        else:
            # far away: the proportional pull does the work, forget the past so
            # we do not sail past the beat once we arrive
            self.integral *= max(0.0, 1.0 - dt / 0.18)
        target = self.kp * e + self.ki * self.integral
        blend = min(1.0, dt / max(self.tau, 1e-3))
        self._corr += (target - self._corr) * blend
        self._corr = max(-self.clamp * 2, min(self.clamp * 2, self._corr))

    def tempo_factor(self) -> float:
        return 1.0 + max(-self.clamp, min(self.clamp, self._corr))

    def timing_offset(self) -> float:
        return max(-self.offset_clamp, min(self.offset_clamp, self._corr * 0.35))

    @property
    def phase_error_ms(self) -> float:
        return self.last_error * 1000.0

    @property
    def mean_abs_ms(self) -> float:
        return (self.error_abs_sum / self.samples * 1000.0) if self.samples else 0.0


# ----------------------------------------------------------------- balance

@dataclass
class Balance:
    """Keep the two voices audible together without flattening the difference.

    We follow the partner with a 150 ms filter and aim for a fixed loudness
    gap, so a crescendo in one voice pulls the other one back — but only part
    of the way.
    """

    gap_db: float = 2.5
    tau: float = 0.15
    scale: float = 1.0
    lo: float = 0.55
    hi: float = 1.45
    _partner_db: float = 72.0
    samples: int = 0

    @staticmethod
    def _db(v: float) -> float:
        return 20.0 * math.log10(max(v, 1.0))

    def observe(self, partner_vel: float, dt: float) -> None:
        self.samples += 1
        blend = min(1.0, dt / max(self.tau, 1e-3))
        self._partner_db += (self._db(partner_vel) - self._partner_db) * blend
        # if the partner is loud, sit under them; if soft, come forward
        target = 10 ** ((-self.gap_db - (self._partner_db - 72.0) * 0.25) / 20.0)
        self.scale += (max(self.lo, min(self.hi, target * 1.05)) - self.scale) * blend


# ------------------------------------------------------------------- pedal

@dataclass
class PedalWatch:
    """Adaptive sustain. Dense or loud music gets shorter pedal, on the fly."""

    base_beats: float = 2.0
    floor: float = 0.5
    hold: float = 2.0
    _density: float = 0.25
    _level: float = 0.6

    def observe(self, notes_per_beat: float, level: float, dt: float) -> None:
        blend = min(1.0, dt / 0.20)
        self._density += (notes_per_beat - self._density) * blend
        self._level += (level - self._level) * blend
        shrink = 1.0 / (1.0 + 2.2 * self._density) * (1.0 / (0.7 + 0.9 * self._level))
        self.hold = max(self.floor, min(self.base_beats, self.base_beats * shrink))

    def release_at(self, beat_in_bar: float, bar_beats: float) -> float:
        """When to lift inside the bar, given the current hold length."""
        return min(bar_beats - 0.05, beat_in_bar + self.hold)


# ---------------------------------------------------------------- reactions

@dataclass
class Reaction:
    """What we measured about how fast we answered the partner."""

    latencies: list[float] = field(default_factory=list)
    last_partner_onset: float = 0.0

    def partner_onset(self, t: float) -> None:
        self.last_partner_onset = t

    def note_fired(self, t: float) -> None:
        if self.last_partner_onset:
            self.latencies.append((t - self.last_partner_onset) * 1000.0)

    @property
    def p50_ms(self) -> float:
        if not self.latencies:
            return 0.0
        s = sorted(self.latencies)
        return round(s[len(s) // 2], 2)

    @property
    def p95_ms(self) -> float:
        if not self.latencies:
            return 0.0
        s = sorted(self.latencies)
        return round(s[min(len(s) - 1, int(len(s) * 0.95))], 2)

    @property
    def max_ms(self) -> float:
        return round(max(self.latencies), 2) if self.latencies else 0.0
