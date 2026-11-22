"""Generate the two-voice example used by the README tests."""
from __future__ import annotations
import random
import mido

def build(path: str, notes: list[tuple[int, int, int, int]], ch: int, tpb: int = 480) -> None:
    mid = mido.MidiFile(ticks_per_beat=tpb)
    tr = mido.MidiTrack()
    mid.tracks.append(tr)
    tr.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(84), time=0))
    events: list[tuple[int, int, mido.Message]] = []
    for start, pitch, dur, vel in notes:
        events.append((start, 1, mido.Message("note_on", note=pitch, velocity=vel, channel=ch)))
        events.append((start + dur, 0, mido.Message("note_off", note=pitch, velocity=0, channel=ch)))
    events.sort(key=lambda e: (e[0], e[1]))
    now = 0
    for tick, _, msg in events:
        msg.time = tick - now
        tr.append(msg)
        now = tick
    mid.save(path)
    print(f"{path}: {len(notes)} notes")

def main() -> None:
    rng = random.Random(5)
    a, b = [], []
    bpb, tpb = 4, 480
    for bar in range(8):
        base = bar * bpb * tpb
        a.append((base, 62 + 12 + [0, 2, 4, 7][bar % 4], int(1.6 * tpb), rng.randint(72, 96)))
        a.append((base + 2 * tpb, 62 + 12 + [4, 7, 9, 12][bar % 4], int(1.7 * tpb), rng.randint(68, 92)))
        b.append((base, 62 - 12 + [0, 5][bar % 2], int(1.9 * tpb), rng.randint(58, 78)))
        b.append((base + 2 * tpb, 62 - 12 + [7, 0][bar % 2], int(1.9 * tpb), rng.randint(56, 76)))
    build("example_a.mid", a, ch=0)
    build("example_b.mid", b, ch=1)

if __name__ == "__main__":
    main()
