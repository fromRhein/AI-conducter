"""Load the MIDI the user brings, slice it into bars, keep it honest.

The models do not invent notes any more: they *perform* the score you hand
them. This module turns a .mid (or two) into per-bar note lists in beats,
which is the only thing a player needs to know before adding timing, dynamics
and pedal.

    python score.py --probe song.mid       # tracks, channels, bars
    from score import load_voice, bars_of
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import mido


@dataclass
class Scored:
    beat: float          # absolute position in beats from the start
    note: int
    vel: int
    dur: float           # in beats
    ch: int


def load_track(path: str | Path, track: int | None = None) -> list[Scored]:
    """Absolute-beat note list for one track (or all tracks merged)."""
    mf = mido.MidiFile(str(path))
    tpb = mf.ticks_per_beat or 480
    out: list[Scored] = []
    open_notes: dict[tuple[int, int], tuple[float, int]] = {}

    tracks = [mf.tracks[track]] if track is not None else mf.tracks
    for tr in tracks:
        tick = 0
        for msg in tr:
            tick += msg.time
            if msg.type == "note_on" and msg.velocity > 0:
                open_notes[(msg.channel, msg.note)] = (tick / tpb, msg.velocity)
            elif msg.type in ("note_off",) or (msg.type == "note_on" and msg.velocity == 0):
                key = (msg.channel, msg.note)
                if key in open_notes:
                    start, vel = open_notes.pop(key)
                    out.append(Scored(start, msg.note, vel, tick / tpb - start, msg.channel))
    out.sort(key=lambda n: (n.beat, n.note))
    return out


def bars_of(notes: list[Scored], beats_per_bar: int) -> dict[int, list[Scored]]:
    """Bucket notes into bars; a note leaking over the barline stays in its own bar."""
    bars: dict[int, list[Scored]] = {}
    for n in notes:
        b = int(n.beat // beats_per_bar)
        bars.setdefault(b, []).append(n)
    return bars


def to_brief(notes: list[Scored], bar: int, beats_per_bar: int) -> list[dict]:
    """Compact payload for the model: beat inside the bar, note, dur, vel."""
    row = []
    for n in notes:
        off = n.beat - bar * beats_per_bar
        if off < 0:
            continue
        row.append({
            "beat": round(off, 3),
            "note": int(n.note),
            "dur": round(min(n.dur, beats_per_bar - off), 3),
            "vel": int(n.vel),
        })
    return row


def describe(path: str | Path) -> None:
    mf = mido.MidiFile(str(path))
    print(f"{path}: {mf.type} tracks={len(mf.tracks)} tpb={mf.ticks_per_beat} "
          f"len={mf.length:.2f}s")
    for i, tr in enumerate(mf.tracks):
        notes = load_track(path, track=i)
        chans = sorted({n.ch for n in notes})
        lo = min((n.note for n in notes), default=0)
        hi = max((n.note for n in notes), default=0)
        last = max((n.beat + n.dur for n in notes), default=0.0)
        print(f"  [{i}] {tr.name!r:28s} notes={len(notes):4d} ch={chans} "
              f"range={lo}-{hi} bars={last / 4:.1f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    a = ap.parse_args()
    describe(a.file)
