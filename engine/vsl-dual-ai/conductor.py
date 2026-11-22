"""Real-time engine: two coupled clocks, one piano, reflexes in the loop.

The previous version asked a model for every bar. That is not playing, that is
rehearsing in chunks. Here the loop runs at `tick_ms` (default 4 ms):

  * each voice advances its own beat clock at its own tempo;
  * the two clocks are coupled by a PLL on the partner's onsets, so they lock
    to each other the way a duo does, not to a click;
  * velocity, pedal and CC come from curves written before the run, sampled
    continuously, and nudged by the balance/pedal reflexes;
  * a model is only asked at structural points, with a hard deadline
    (`deadline_ms`, default 220 ms). Late answer = ignored, never audible.

Notes fire when a voice's beat clock crosses them, so a tempo change takes
effect on the very next note instead of at the next bar line.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import curves
import reading
from agents import Canned, Model, ModelCfg
from bus import ParamRegistry, Scheduler
from ensemble import Balance, PLL, PedalWatch, Reaction
from midiwin import MidiOut
from score import bars_of, load_track

ROOT = Path(__file__).parent


def load_cfg(path: Path = ROOT / "config.json") -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class Voice:
    """One player: its own clock, its own reflexes, its own channel."""

    def __init__(self, side: str, cfg: dict, notes, plan: curves.Plan) -> None:
        self.side = side
        self.ch = 0 if side == "A" else 1
        self.notes = sorted(notes, key=lambda n: n.beat)
        self.idx = 0
        self.plan = plan
        self.pll = PLL(**cfg.get("pll", {}))
        self.balance = Balance(gap_db=cfg.get("gap_db", 2.5))
        self.pedal = PedalWatch()
        self.beat = 0.0
        self.hanging: list[str] = []
        self.notes_fired = 0
        self.last_onset = 0.0
        self.pedal_down = False
        self.pedal_release_beat = 0.0
        self.partner: Voice | None = None
        self.onsets: dict[float, float] = {}
        self.detune_done = False
        self.wobble = 0.0
        self.bias = 0.0 if side == "A" else 0.0
        if cfg.get("humanize", {}).get("enabled", True):
            self.bias = float(cfg["humanize"].get(f"bias_{side.lower()}", 0.0))
            self.wobble_gain = float(cfg["humanize"].get("wobble", 0.0045))
            self.wobble_tau = float(cfg["humanize"].get("tau_s", 0.35))
        else:
            self.wobble_gain = 0.0
            self.wobble_tau = 1.0


class Engine:
    def __init__(self, cfg: dict, bars: int, demo: bool = False,
                 score: tuple[str, str] | None = None) -> None:
        self.cfg = cfg
        self.demo = demo
        self.bpb = cfg["beats_per_bar"]
        self.bpm = float(cfg["bpm"])
        self.tick = float(cfg.get("engine", {}).get("tick_ms", 4)) / 1000.0
        self.deadline = float(cfg.get("engine", {}).get("deadline_ms", 220)) / 1000.0
        self.boundary_beats = float(cfg.get("engine", {}).get("boundary_beats", 8))
        self.sched = Scheduler()
        self.midi = MidiOut(cfg["midi_port"])
        self.pool = ThreadPoolExecutor(max_workers=2)
        self.reaction = Reaction()
        self._last_cc = 0.0
        self.jitter: list[float] = []
        self.gestures: list[dict] = []
        self.late_gestures = 0
        self.relock_ms: float | None = None
        self.last_beat = 0.0
        self.pending: dict[str, tuple] = {}
        self._load(score, bars)
        self._arm()

    # ------------------------------------------------------------- loading
    def _load(self, score: tuple[str, str] | None, bars: int) -> None:
        cs = self.cfg.get("score") or {}
        if score and all(score):
            src = {"A": (score[0], 0), "B": (score[1], 0)}
        elif cs.get("a") and cs.get("b"):
            src = {"A": (cs["a"], int(cs.get("a_track", 0))),
                   "B": (cs["b"], int(cs.get("b_track", 0)))}
        else:
            src = {"A": ("example_a.mid", 0), "B": ("example_b.mid", 0)}
        self.notes = {}
        for side, (path, track) in src.items():
            notes = load_track(path, track)
            self.notes[side] = notes
        self.score_name = "+".join(src[s][0] for s in ("A", "B"))
        longest = max(n.beat for ns in self.notes.values() for n in ns)
        self.total_beats = math.ceil(longest / self.bpb) * self.bpb
        self._src = src

    def _arm(self) -> None:
        flat = {s: self.notes[s] for s in ("A", "B")}
        self.digest = reading.digest(flat["A"], flat["B"], self.bpb, self.bpm)
        self.voices: dict[str, Voice] = {}
        self.models: dict[str, object] = {}
        for side, other in (("A", "B"), ("B", "A")):
            plan = curves.build(self.digest, side, float(self.cfg.get("style", 1.0)))
            v = Voice(side, self.cfg, self.notes[side], plan)
            v.partner = None
            self.voices[side] = v
            c = self.cfg["models"][side]
            mcfg = ModelCfg(
                name=c["name"], base_url=c["base_url"], model=c["model"],
                api_key_env=c["api_key_env"], role=c["role"], lo=c["lo"], hi=c["hi"],
                ch=v.ch, style=c["style"], params=", ".join(self.cfg["params"]),
                timeout=float(c.get("timeout", 5.0)),
            )
            self.models[side] = Canned(mcfg) if self.demo else Model(mcfg)
        self.voices["A"].partner = self.voices["B"]
        self.voices["B"].partner = self.voices["A"]
        self.regs = {
            s: ParamRegistry(self.cfg["params"],
                             lambda ch, cc, val, s=s: self.midi.cc(ch, cc, val))
            for s in ("A", "B")
        }

    # -------------------------------------------------------------- reading
    def read_score(self) -> dict[str, str]:
        out_dir = str(ROOT / self.cfg.get("reading", {}).get("out_dir", "readings"))
        cap = int(self.cfg.get("reading", {}).get("max_chars", 2400))
        meta = {"score": self.score_name, "bars": self.digest["bars"], "bpm": self.bpm}
        out = {}
        for side, other in (("A", "B"), ("B", "A")):
            brief = reading.brief_text(self.digest, side)
            text = ""
            if not self.demo:
                text = reading.ask_reading(self.models[side], brief,
                                           self.cfg["models"][other]["name"])
            if not text:
                text = reading.fallback_reading(self.digest, side)
            self.models[side].reading = text[:cap]
            _, pdf = reading.save(text, out_dir, side, meta, d=self.digest)
            out[side] = pdf
            print(f"[read] player {side}: {len(text)} chars -> {pdf}")
        return out

    # --------------------------------------------------------------- gesture
    def _gesture_state(self, side: str, beat: float) -> dict:
        v = self.voices[side]
        p = v.partner
        return {
            "beat": round(beat, 2),
            "bar": int(beat // self.bpb) + 1,
            "tempo_bpm": self.bpm,
            "partner_last_beat": round(p.beat, 2),
            "phase_error_ms": round((p.beat - v.beat) * 60000.0 / self.bpm, 1),
            "partner_vel_mean": round(p.balance._partner_db, 1),
            "your_notes_next_4_beats": [
                {"beat": round(n.beat - beat, 2), "note": n.note, "vel": n.vel}
                for n in v.notes[v.idx:v.idx + 6] if n.beat - beat < 4
            ],
            "beats_per_bar": self.bpb,
            "you_lead": self._is_lead(side, beat),
            "your_score": [
                {"beat": round(n.beat, 2), "note": n.note, "dur": round(n.dur, 2),
                 "vel": n.vel}
                for n in v.notes[v.idx:v.idx + 8] if 0 <= n.beat - beat < self.bpb
            ],
            "partner_just_played": {
                "tempo": round(1.0 + p.bias + p.wobble, 4),
                "vel_mean": round(getattr(p, "last_vel", 0.0) or 0.0, 1),
                "shift_ms": round(p.pll.timing_offset() * 1000.0, 1),
            },
            "limits": {"tempo": [0.97, 1.03], "vel_scale": [0.75, 1.25],
                       "pedal_beats": [0.4, 3.0]},
        }

    def _is_lead(self, side: str, beat: float) -> bool:
        seq = self.cfg.get("leadership") or ["A", "B"]
        span = max(1.0, self.boundary_beats * 2.0)
        return seq[int(beat // span) % len(seq)] == side

    def _dispatch_gestures(self, beat: float) -> None:
        """Submit both players' gestures. Never waits: the tick loop cannot afford it."""
        for side in ("A", "B"):
            if side in self.pending:
                continue
            m = self.models[side]
            if not hasattr(m, "ask"):
                continue
            state = self._gesture_state(side, beat)
            if self.demo:
                def _call(m=m, state=state):
                    time.sleep(random.uniform(0.02, 0.18))
                    return m.ask(state)
                fut = self.pool.submit(_call)
            else:
                fut = self.pool.submit(m.ask, state)
            self.pending[side] = (fut, time.perf_counter() + self.deadline, beat)

    def _poll_gestures(self, now: float) -> list[tuple[str, dict, float]]:
        """Collect what came back in time, drop what did not."""
        done: list[tuple[str, dict, float]] = []
        for side in list(self.pending):
            fut, deadline, beat = self.pending[side]
            if fut.done():
                try:
                    raw = fut.result()
                except Exception:
                    raw = None
                g = self._as_gesture(raw)
                if g is None:
                    self.late_gestures += 1
                else:
                    done.append((side, g, beat))
                self.pending.pop(side, None)
            elif now > deadline:
                self.late_gestures += 1
                self.pending.pop(side, None)
        return done

    @staticmethod
    def _as_gesture(raw: dict | None) -> dict | None:
        """Accept both the bar contract and the gesture contract."""
        if not isinstance(raw, dict):
            return None
        g: dict = {}
        if "tempo" in raw:
            g["tempo"] = float(raw["tempo"])
        if "vel_scale" in raw:
            g["vel_scale"] = float(raw["vel_scale"])
        if "pedal_beats" in raw:
            g["pedal_beats"] = float(raw["pedal_beats"])
        if isinstance(raw.get("params"), dict):
            g["params"] = raw["params"]
        g["say"] = str(raw.get("say", ""))[:40]
        return g if len(g) > 1 else None

    # ------------------------------------------------------------------ run
    def run(self, seconds: float | None = None) -> None:
        total = self.total_beats
        if seconds:
            total = min(total, seconds * self.bpm / 60.0)
        spb = 60.0 / self.bpm
        last = time.perf_counter()
        t0 = last
        next_boundary = 0.0
        while True:
            now = time.perf_counter()
            dt = now - last
            last = now
            lead = self.voices["A"]
            if min(lead.beat, self.voices["B"].beat) >= total:
                break

            # 1) mutual entrainment, then advance both clocks
            err = (self.voices["B"].beat - self.voices["A"].beat) * spb
            self.voices["A"].pll.observe(err, dt)
            self.voices["B"].pll.observe(-err, dt)
            det = self.cfg.get("engine", {}).get("detune")
            for side in ("A", "B"):
                v = self.voices[side]
                plan_tempo = v.plan.tempo.at(v.beat, dt)
                if v.wobble_gain:
                    blend = min(1.0, dt / max(v.wobble_tau, 1e-3))
                    v.wobble += (random.uniform(-1.0, 1.0) * v.wobble_gain - v.wobble) * blend
                tempo = plan_tempo * (1.0 + v.bias + v.wobble) * v.pll.tempo_factor()
                v.beat += dt / (spb / max(tempo, 0.2))
                if det and not v.detune_done and side == det.get("voice", "A")                         and v.beat >= float(det.get("beat", 8)):
                    v.beat -= float(det.get("ms", 30)) / 1000.0 / spb
                    v.detune_done = True
                    self.detune_t = time.perf_counter()
                    self.detune_phase0 = (self.voices["B"].beat - v.beat) * spb * 1000.0
                    print(f"[test] {side} dragged {det.get('ms')} ms at beat {v.beat:.1f}")
            if getattr(self, "detune_t", None) and self.relock_ms is None:
                err_ms = abs((self.voices["B"].beat - self.voices["A"].beat) * spb * 1000.0)
                if err_ms < 3.0:
                    self.relock_ms = (time.perf_counter() - self.detune_t) * 1000.0

            avg_beat = 0.5 * (self.voices["A"].beat + self.voices["B"].beat)

            # 2) fire whatever each clock has crossed
            for side in ("A", "B"):
                self._fire(side, now)

            # 3) reflexes: balance, pedal, CC
            self._reflex(avg_beat, dt)

            # 4) structural gesture, if a model is available
            if avg_beat >= next_boundary and avg_beat < self.last_beat - 0.5:
                self._dispatch_gestures(avg_beat)
                next_boundary = avg_beat + self.boundary_beats

            # 4b) pick up whatever the players have already decided
            for side, g, gbeat in self._poll_gestures(now):
                applied = curves.blend_gesture(self.voices[side].plan, gbeat, g)
                if applied:
                    self.gestures.append({"beat": round(gbeat, 2), "side": side,
                                          "applied": applied})
                    print(f"[{side}] gesture @{gbeat:.1f}: {', '.join(applied)}")

            # 5) sleep to the next tick, with a short spin at the end
            target = now + self.tick
            while time.perf_counter() < target - 0.0012:
                time.sleep(0.0005)
            while time.perf_counter() < target:
                pass
            self.jitter.append((time.perf_counter() - target) * 1000.0)

        # let the last chord ring, then stop
        time.sleep(1.2)
        self.stop(t0)

    def _fire(self, side: str, now: float) -> None:
        v = self.voices[side]
        spb = 60.0 / self.bpm
        # a late player does not just speed up, it plays the next note early:
        # up to 25 ms of one-shot phase correction on top of the tempo pull
        lead_beats = -v.pll.timing_offset() / spb
        while v.idx < len(v.notes) and v.notes[v.idx].beat <= v.beat + lead_beats:
            n = v.notes[v.idx]
            v.idx += 1
            plan_v = v.plan.vel.at(v.beat)
            vel = int(max(1, min(127, round(n.vel * plan_v * v.balance.scale))))
            self.midi.note_on(v.ch, n.note, vel)
            dur = max(0.08, n.dur * spb / max(v.plan.tempo.at(v.beat), 0.2))
            self.sched.submit(now + dur, lambda ch=v.ch, nn=n.note: self.midi.note_off(ch, nn))
            v.notes_fired += 1
            v.last_vel = vel
            v.last_onset = now
            v.onsets[round(n.beat, 3)] = now
            p = v.partner
            if p is not None and p.last_onset and (now - p.last_onset) < 0.12:
                self.reaction.note_fired(now)
            # our lateness against our own ideal beat time
            self.jitter.append((v.beat - n.beat) * spb * 1000.0)
            if v.partner is not None:
                v.partner.balance.observe(vel, max(now - v.partner.last_onset, 1e-3))

    def _reflex(self, beat: float, dt: float) -> None:
        spb = 60.0 / self.bpm
        bar_pos = beat % self.bpb
        for side in ("A", "B"):
            v = self.voices[side]
            self.last_beat = max(self.last_beat, v.notes[-1].beat if v.notes else 0.0)
            # pedal: recompute the release point every tick, so a sudden dense
            # passage shortens the sustain instead of waiting for the next bar
            density = self.digest["per_bar"][min(int(beat // self.bpb),
                                                len(self.digest["per_bar"]) - 1)]
            dens = ((density["a"] + density["b"]) / self.bpb) / 4.0
            v.pedal.observe(dens, v.plan.vel.at(beat) / 1.4, dt)
            if bar_pos < 0.35 and not v.pedal_down:
                self.midi.cc(v.ch, 64, 127)
                v.pedal_down = True
                v.pedal_release_beat = v.pedal.release_at(bar_pos, self.bpb)
            elif v.pedal_down and bar_pos >= v.pedal_release_beat:
                self.midi.cc(v.ch, 64, 0)
                v.pedal_down = False
        # CC curves at 20 Hz, each parameter rate-limited inside the registry
        if time.perf_counter() - self._last_cc > 0.05:
            self._last_cc = time.perf_counter()
            for side in ("A", "B"):
                v = self.voices[side]
                for name, curve in v.plan.cc.items():
                    self.regs[side].apply(name, curve.at(beat), v.ch, who=side)

    # ----------------------------------------------------------------- stop
    def stop(self, t0: float) -> None:
        for ch in (0, 1):
            self.midi.cc(ch, 64, 0)
            self.midi.all_notes_off(ch)
        time.sleep(0.25)
        self.sched.stop()
        self.pool.shutdown(wait=False)
        st = self.sched.stats()
        a, b = self.voices["A"], self.voices["B"]
        jit = sorted(self.jitter) or [0.0]
        common = set(a.onsets) & set(b.onsets)
        pairs = sorted((a.onsets[k], abs(a.onsets[k] - b.onsets[k]) * 1000.0) for k in common)
        asynch = sorted(v for _t, v in pairs) or [0.0]
        settled_t = (self.detune_t + (self.relock_ms or 0.0) / 1000.0) if getattr(self, "detune_t", None) else 0.0
        settled = sorted(v for t, v in pairs if t >= settled_t) or [0.0]
        out = {
            "runtime_s": round(time.perf_counter() - t0, 2),
            "ticks": len(self.jitter),
            "tick_p50_ms": round(jit[len(jit) // 2], 2),
            "tick_p99_ms": round(jit[min(len(jit) - 1, int(len(jit) * 0.99))], 2),
            "notes": a.notes_fired + b.notes_fired,
            "midi_events": st["events"],
            "midi_late_avg_ms": st["late_avg_ms"],
            "midi_late_max_ms": st["late_max_ms"],
            "phase_A_ms": round(a.pll.phase_error_ms, 2),
            "phase_B_ms": round(b.pll.phase_error_ms, 2),
            "phase_mean_abs_ms": round(0.5 * (a.pll.mean_abs_ms + b.pll.mean_abs_ms), 2),
            "asynchrony_p50_ms": round(asynch[len(asynch) // 2], 2),
            "asynchrony_p95_ms": round(asynch[min(len(asynch) - 1, int(len(asynch) * 0.95))], 2),
            "asynchrony_max_ms": round(asynch[-1], 2),
            "asynchrony_settled_p95_ms": round(settled[min(len(settled) - 1, int(len(settled) * 0.95))], 2),
            "asynchrony_settled_max_ms": round(settled[-1], 2),
            "asynchrony_over_15ms": sum(1 for v in asynch if v > 15.0),
            "relock_ms": (round(self.relock_ms, 1) if self.relock_ms else None),
            "reaction_p50_ms": self.reaction.p50_ms,
            "reaction_p95_ms": self.reaction.p95_ms,
            "reaction_max_ms": self.reaction.max_ms,
            "gestures_applied": len(self.gestures),
            "gestures_late": self.late_gestures,
            "score": self.score_name,
        }
        print(json.dumps(out, indent=1))
        (ROOT / "run.log").write_text(json.dumps(
            {"stats": out, "gestures": self.gestures}, indent=1), encoding="utf-8")
        self.midi.close()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bars", type=int, default=8)
    ap.add_argument("--seconds", type=float, default=None)
    ap.add_argument("--demo", action="store_true", help="no API calls")
    ap.add_argument("--score", nargs=2, metavar=("VOICE_A.mid", "VOICE_B.mid"))
    ap.add_argument("--config", default=str(ROOT / "config.json"))
    ap.add_argument("--read", dest="read", action="store_true", default=None)
    ap.add_argument("--no-read", dest="read", action="store_false")
    ap.add_argument("--detune", type=float, default=None,
                    help="test: drag voice A by N ms mid-piece and measure re-lock")
    args = ap.parse_args()
    cfg = load_cfg(Path(args.config))
    if args.detune is not None:
        cfg.setdefault("engine", {})["detune"] = {
            "voice": "A", "beat": max(4.0, min(args.bars * cfg["beats_per_bar"] / 2.0, args.bars * cfg["beats_per_bar"] - 6.0)),
            "ms": args.detune}
    e = Engine(cfg, args.bars, demo=args.demo,
               score=tuple(args.score) if args.score else None)
    want = cfg.get("reading", {}).get("enabled", True) if args.read is None else args.read
    if want:
        e.read_score()
    try:
        e.run(args.seconds)
    except KeyboardInterrupt:
        e.stop(time.perf_counter())


if __name__ == "__main__":
    main()
