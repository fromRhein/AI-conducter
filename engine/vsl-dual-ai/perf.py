"""What a model is allowed to decide, and how two decisions become one sound.

A player gets the score for one bar plus what the partner just did, and answers
with a *performance*, not with notes:

    {"tempo": 0.97, "shift_ms": 6, "vel_scale": 1.1,
     "vel": {"0": 92, "1.5": 78}, "pedal": [{"beat": 0, "v": 127}],
     "params": {"reverb": 0.3}, "say": "pushed the third beat"}

Two performers cannot hold two tempos at once. So one of them leads the bar and
the other only bends it: the follower's wish is honoured by at most
`follow_pull` of its distance from the leader (default 35 %, clamped to ±3 %).
The same guard runs on dynamics, so nobody drowns the other.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Decision:
    tempo: float = 1.0
    shift_ms: float = 0.0
    vel_scale: float = 1.0
    vel: dict[int, int] = field(default_factory=dict)
    pedal: list[tuple[float, int]] = field(default_factory=list)
    params: dict[str, float] = field(default_factory=dict)
    say: str = ""
    raw_ok: bool = True


def parse_decision(raw: dict, limits: dict) -> tuple[Decision, list[str]]:
    """Clamp everything; a wild answer degrades, it never breaks the bar."""
    bad: list[str] = []
    d = Decision()
    if not isinstance(raw, dict):
        return Decision(raw_ok=False), ["not an object"]

    def num(key: str, lo: float, hi: float, default: float) -> float:
        try:
            v = float(raw.get(key, default))
        except Exception:
            bad.append(f"{key} not numeric")
            return default
        if not (lo <= v <= hi):
            bad.append(f"{key} {v} clipped to [{lo},{hi}]")
            v = max(lo, min(hi, v))
        return v

    d.tempo = num("tempo", limits["tempo"][0], limits["tempo"][1], 1.0)
    d.shift_ms = num("shift_ms", -limits["shift_ms"], limits["shift_ms"], 0.0)
    d.vel_scale = num("vel_scale", limits["vel_scale"][0], limits["vel_scale"][1], 1.0)

    for k, v in (raw.get("vel") or {}).items():
        try:
            d.vel[int(float(k))] = max(1, min(127, int(v)))
        except Exception:
            bad.append(f"vel['{k}'] invalid")

    for ev in (raw.get("pedal") or [])[:6]:
        try:
            d.pedal.append((float(ev["beat"]), max(0, min(127, int(ev["v"])))))
        except Exception:
            bad.append("pedal event invalid")

    for name, v in (raw.get("params") or {}).items():
        try:
            d.params[str(name)] = max(0.0, min(1.0, float(v)))
        except Exception:
            bad.append(f"param {name} invalid")

    d.say = str(raw.get("say", ""))[:80]
    return d, bad


def negotiate(lead: Decision, follow: Decision, cfg: dict) -> tuple[float, dict]:
    """One shared tempo for the bar, plus an audit trail."""
    pull = float(cfg.get("follow_pull", 0.35))
    band = float(cfg.get("follow_band", 0.03))
    lo, hi = cfg["tempo"]
    want = lead.tempo
    dist = max(-band, min(band, follow.tempo - want))
    eff = max(lo, min(hi, want + dist * pull))
    return eff, {
        "lead_tempo": round(want, 4),
        "follow_tempo": round(follow.tempo, 4),
        "applied": round(eff, 4),
        "bent": round(eff - want, 4),
    }


def balance(a: Decision, b: Decision, cap_db: float = 4.0) -> tuple[Decision, Decision]:
    """Stop one voice from burying the other; ratio capped to ~cap_db."""
    ratio = (a.vel_scale + 1e-6) / (b.vel_scale + 1e-6)
    limit = 10 ** (cap_db / 20)
    if ratio > limit:
        a.vel_scale = b.vel_scale * limit
    elif ratio < 1 / limit:
        b.vel_scale = a.vel_scale * limit
    return a, b


def realise(notes: list[dict], d: Decision, beats_per_bar: int) -> list[tuple[float, int, int, float]]:
    """(beat, note, velocity, duration) after the player's vel decisions."""
    out = []
    for n in notes:
        key = round(n["beat"])
        vel = d.vel.get(key)
        if vel is None:
            vel = int(round(n.get("vel", 80) * d.vel_scale))
        out.append((n["beat"], int(n["note"]), max(1, min(127, vel)),
                    float(n.get("dur", 0.5))))
    return out
