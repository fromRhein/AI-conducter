"""Two players, one contract.

The models are *performers*, not composers: the score is supplied, their job is
tempo, timing, dynamics, pedal and sampler colour, and reacting to the partner.
Both run against OpenAI-compatible /chat/completions and answer one bar at a
time in JSON. `Canned` implements the same contract locally so the MIDI path can
be tested with no API key at all.
"""
from __future__ import annotations

import json
import math
import os
import urllib.error
import urllib.request
from dataclasses import dataclass

SYSTEM = """You are {name}, one player of a two-piano duo on a VSL Steinway D-274.
You do NOT compose. The score of your voice is given as `your_score`
(beat, note, dur, vel). You decide how this bar is PLAYED.

What you control:
- `tempo`: multiplier for the bar, 1.0 = {bpm} BPM. Allowed range given in `limits`.
- `shift_ms`: your own micro-timing against the grid, in ms (late = positive).
- `vel_scale`: 0.45..1.6, your dynamic level for this bar.
- `vel`: optional per-note velocity override, keyed by beat inside the bar.
- `pedal`: sustain CC64 events inside the bar, [{{"beat":0,"v":127}}, ...].
- `params`: sampler colour, only these keys: {params}. Values 0..1.

How the duo stays together:
- One player is `leader` this bar; the other's tempo wish only bends the leader.
- If you are the follower, copy the partner's direction, add at most a small push.
- `partner_just_played` holds the numbers the partner actually produced last bar
  (vel_mean, tempo, shift_ms) plus its comment. `heard` is the audio analysis.
- React: answer the partner's gesture. Do not repeat the same shape every bar.

Rules:
- JSON only, no prose outside the object.
- 2 to 8 pedal events. Do not write notes; only the keys above.
- `say` is under 12 words, for your partner.
Your role: {role}. Style: {style}.
"""


@dataclass
class ModelCfg:
    name: str
    base_url: str
    model: str
    api_key_env: str
    role: str
    lo: int
    hi: int
    ch: int
    style: str
    params: str
    temperature: float = 0.85
    timeout: float = 6.0


class Model:
    def __init__(self, cfg: ModelCfg) -> None:
        self.cfg = cfg
        self.key = os.environ.get(cfg.api_key_env, "")
        self.calls = 0
        self.fails = 0
        self.reading = ""          # written before the first bar, then quoted every bar

    def _post(self, body: dict) -> dict | None:
        req = urllib.request.Request(
            self.cfg.base_url.rstrip("/") + "/chat/completions",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {self.key}"},
        )
        with urllib.request.urlopen(req, timeout=self.cfg.timeout) as r:
            return json.loads(r.read().decode())

    def ask_text(self, system: str, user: str) -> str:
        """Free-form answer (used by the score-reading stage, not the bar loop)."""
        if not self.key:
            return ""
        self.calls += 1
        try:
            payload = self._post({
                "model": self.cfg.model,
                "messages": [{"role": "system", "content": system},
                             {"role": "user", "content": user}],
                "temperature": 0.7,
                "max_tokens": 1400,
            })
            return payload["choices"][0]["message"]["content"].strip()
        except (urllib.error.URLError, KeyError, json.JSONDecodeError, TimeoutError) as exc:
            self.fails += 1
            print(f"[{self.cfg.name}] reading failed: {type(exc).__name__}: {exc}")
            return ""

    def _prompt(self, state: dict) -> tuple[str, str]:
        c = self.cfg
        system = SYSTEM.format(
            name=c.name, bpm=state["tempo_bpm"], params=c.params,
            role=c.role, style=c.style,
        )
        if self.reading:
            system += ("\n\nYOUR OWN READING OF THIS SCORE, written before you started. "
                       "Play what it says; quote it to yourself when unsure:\n" + self.reading)
        return system, json.dumps(state, ensure_ascii=False)

    def ask(self, state: dict) -> dict | None:
        if not self.key:
            return None
        system, user = self._prompt(state)
        body = {
            "model": self.cfg.model,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
            "temperature": self.cfg.temperature,
            "max_tokens": 500,
            "response_format": {"type": "json_object"},
        }
        self.calls += 1
        try:
            payload = self._post(body)
            return json.loads(payload["choices"][0]["message"]["content"])
        except (urllib.error.URLError, KeyError, json.JSONDecodeError, TimeoutError) as exc:
            self.fails += 1
            print(f"[{self.cfg.name}] failed: {type(exc).__name__}: {exc}")
            return None


class Canned:
    """Offline player: musical reactions without any model, for wiring tests."""

    def __init__(self, cfg: ModelCfg) -> None:
        self.cfg = cfg
        self.calls = 0
        self.fails = 0

    def ask(self, state: dict) -> dict:
        self.calls += 1
        bar = int(state.get("bar", 1))
        lead = bool(state.get("you_lead", True))
        partner = state.get("partner_just_played") or {}
        p_tempo = float(partner.get("tempo", 1.0) or 1.0)
        p_vel = float(partner.get("vel_mean", 0) or 0)
        p_shift = float(partner.get("shift_ms", 0.0) or 0.0)

        # tempo: leader shapes the phrase, follower copies with a small push
        breath = 0.02 * math.sin(bar * 0.9)
        if lead:
            tempo = 1.0 + breath
            shift = 4.0 * math.sin(bar * 1.3)
        else:
            tempo = 1.0 + (p_tempo - 1.0) * 0.6 + breath * 0.4
            shift = p_shift * 0.5

        # gesture contract for the real-time engine (tempo/vel/pedal/params only)
        self.last_gesture = {
            "tempo": round(tempo, 4),
            "vel_scale": 1.0,
            "pedal_beats": round(1.4 + 0.6 * math.sin(bar * 0.7), 2),
            "params": {"reverb": round(0.45 + 0.1 * math.sin(bar), 3),
                       "dynamic": round(0.62 + 0.08 * math.cos(bar * 1.1), 3)},
            "say": "跟着你走" if not lead else "我先起一句",
        }

        # dynamics: answer the partner, never mirror it exactly
        if p_vel:
            vel_scale = max(0.6, min(1.4, 1.0 + (74 - p_vel) / 90.0))
        else:
            vel_scale = 1.0

        score = state.get("your_score") or []
        vel = {}
        for n in score:
            key = int(round(n["beat"]))
            slope = 1.0 - 0.12 * (n["beat"] / max(state.get("beats_per_bar", 4), 1))
            vel[str(key)] = int(max(1, min(127, round(n.get("vel", 80) * vel_scale * slope))))

        pedal = [{"beat": 0, "v": 127}] if bar % 2 == 0 else []
        if bar % 2 == 0:
            pedal.append({"beat": round(state.get("beats_per_bar", 4) * 0.62, 2), "v": 0})

        return {
            "tempo": round(tempo, 4),
            "shift_ms": round(shift, 2),
            "vel_scale": round(vel_scale, 3),
            "vel": vel,
            "pedal": pedal,
            "params": {"dynamic": 0.5 + 0.08 * math.sin(bar * 0.5)},
            "say": f"bar {bar} {'lead' if lead else 'follow'}",
        }
