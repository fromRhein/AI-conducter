"""The written interpretation, turned into curves the engine can read at 100 Hz.

A model cannot emit a tempo at 8 ms intervals, and it does not need to: it
writes a shape (where the phrase leans, how much, what the pedal does), and the
engine samples that shape continuously. Everything here is piecewise linear and
slew limited, so a late or wild gesture can never make the piano jump.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Curve:
    """beat -> value, linearly interpolated, with a slew limit per beat."""

    points: list[tuple[float, float]] = field(default_factory=lambda: [(0.0, 1.0)])
    slew: float = 0.02
    _last_beat: float | None = field(default=None, repr=False)
    _last_value: float | None = field(default=None, repr=False)

    def raw(self, beat: float) -> float:
        pts = self.points
        if beat <= pts[0][0]:
            return pts[0][1]
        if beat >= pts[-1][0]:
            return pts[-1][1]
        for (b0, v0), (b1, v1) in zip(pts, pts[1:]):
            if b0 <= beat <= b1:
                if b1 - b0 < 1e-9:
                    return v1
                k = (beat - b0) / (b1 - b0)
                return v0 + (v1 - v0) * k
        return pts[-1][1]

    def at(self, beat: float, dt: float = 0.0) -> float:
        """Slew-limited read: the value can only move so fast per real second."""
        v = self.raw(beat)
        if self._last_value is None or self._last_beat is None:
            self._last_beat, self._last_value = beat, v
            return v
        span = max(abs(beat - self._last_beat), 1e-6)
        limit = self.slew * max(span, dt * 4.0)
        v = max(self._last_value - limit, min(self._last_value + limit, v))
        self._last_beat, self._last_value = beat, v
        return v


@dataclass
class Plan:
    tempo: Curve
    vel: Curve
    pedal_beats: Curve
    cc: dict[str, Curve]
    notes: list[str] = field(default_factory=list)


def _arch(start: float, end: float, low: float, high: float) -> list[tuple[float, float]]:
    """One phrase: lean back at the start, peak just past the middle, settle."""
    span = max(end - start, 0.5)
    return [
        (start, low),
        (start + span * 0.15, low + (high - low) * 0.55),
        (start + span * 0.62, high),
        (end, low + (high - low) * 0.15),
    ]


def build(d: dict, who: str, style: float = 1.0) -> Plan:
    """Deterministic plan from the score digest. `style` scales the rubato."""
    bpb = d["beats_per_bar"]
    bars = d["bars"]
    total = bars * bpb
    mine = "a" if who == "A" else "b"
    theirs = "b" if who == "A" else "a"

    tempo_pts: list[tuple[float, float]] = [(0.0, 0.985)]
    vel_pts: list[tuple[float, float]] = [(0.0, 0.95)]
    pedal_pts: list[tuple[float, float]] = [(0.0, 2.0)]
    for lo, hi in d["phrases"]:
        b0 = (lo - 1) * bpb
        b1 = min(total, hi * bpb)
        tempo_pts += _arch(b0, b1, 0.982, 0.982 + 0.028 * style)
        vel_pts += _arch(b0, b1, 0.92, 0.92 + 0.22 * style)

    for row in d["per_bar"]:
        b = (row["bar"] - 1) * bpb
        density = (row[mine] + row[theirs]) / max(bpb, 1)
        pedal_pts.append((b, max(0.6, 2.4 - 1.5 * density)))
    tempo_pts.sort()
    vel_pts.sort()
    pedal_pts.sort()

    cc = {
        "reverb": Curve([(0.0, 0.42), (total, 0.48)], slew=0.01),
        "dynamic": Curve([(0.0, 0.55)] + [
            ((r["bar"] - 1) * bpb, min(0.85, 0.45 + r[mine] * 0.06)) for r in d["per_bar"]
        ], slew=0.02),
        "mic_main": Curve([(0.0, 0.72)], slew=0.01),
        "mic_close": Curve([(0.0, 0.55)], slew=0.01),
        "send": Curve([(0.0, 0.30)], slew=0.01),
        "smooth_attack": Curve([(0.0, 0.12)], slew=0.01),
    }
    return Plan(
        tempo=Curve(tempo_pts, slew=0.012),
        vel=Curve(vel_pts, slew=0.06),
        pedal_beats=Curve(pedal_pts, slew=0.25),
        cc=cc,
        notes=[f"{who}: {len(d['phrases'])} phrases, {total} beats"],
    )


def blend_gesture(plan: Plan, beat: float, gesture: dict, span: float = 8.0) -> list[str]:
    """Fold a model's mid-flight decision into the curves, without jumps.

    A gesture is a nudge, not a rewrite: capped at ±3 % tempo, ±0.25 dynamics,
    and only over the next `span` beats.
    """
    applied: list[str] = []
    t = gesture.get("tempo")
    if isinstance(t, (int, float)):
        t = max(0.97, min(1.03, float(t)))
        base = plan.tempo.raw(beat)
        plan.tempo.points += [(beat, base), (beat + span * 0.5, base * t), (beat + span, base)]
        plan.tempo.points.sort()
        applied.append(f"tempo x{t:.3f}")
    v = gesture.get("vel_scale")
    if isinstance(v, (int, float)):
        v = max(0.75, min(1.25, float(v)))
        base = plan.vel.raw(beat)
        plan.vel.points += [(beat, base), (beat + span * 0.5, base * v), (beat + span, base)]
        plan.vel.points.sort()
        applied.append(f"vel x{v:.2f}")
    p = gesture.get("pedal_beats")
    if isinstance(p, (int, float)):
        p = max(0.4, min(3.0, float(p)))
        plan.pedal_beats.points += [(beat, plan.pedal_beats.raw(beat)), (beat + span, p)]
        plan.pedal_beats.points.sort()
        applied.append(f"pedal {p:.2f} beats")
    for name, value in (gesture.get("params") or {}).items():
        if name in plan.cc and isinstance(value, (int, float)):
            value = max(0.0, min(1.0, float(value)))
            plan.cc[name].points += [(beat, plan.cc[name].raw(beat)), (beat + span, value)]
            plan.cc[name].points.sort()
            applied.append(f"{name}={value:.2f}")
    return applied
