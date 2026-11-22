"""Minimal Windows MIDI output via winmm (no rtmidi / no extra wheels).

Why: python-rtmidi has no wheel for Python 3.15 yet, and mido needs a backend.
winmm gives us the same short-message API with ~1 ms scheduling jitter.

Usage:
    from midiwin import ports, MidiOut
    print(ports())                 # ['loopMIDI Port 1', ...]
    m = MidiOut('loopMIDI Port 1')
    m.note_on(ch=0, note=60, vel=90)
    m.note_off(ch=0, note=60)
    m.cc(ch=0, num=21, value=80)
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import os

winmm = ctypes.WinDLL("winmm")

# ---- types ----------------------------------------------------------------
MAXPNAMELEN = 32


class MIDIOUTCAPS(ctypes.Structure):
    _fields_ = [
        ("wMid", wt.WORD),
        ("wPid", wt.WORD),
        ("vDriverVersion", wt.UINT),
        ("szPname", wt.WCHAR * MAXPNAMELEN),
        ("wTechnology", wt.WORD),
        ("wVoices", wt.WORD),
        ("wNotes", wt.WORD),
        ("wChannelMask", wt.WORD),
        ("dwSupport", wt.DWORD),
    ]


MIDIERR_NODEVICE = 68
CALLBACK_NULL = 0x00000000


def _err(code: int) -> None:
    if code != 0:
        raise OSError(f"winmm MIDI error {code}")


def ports() -> list[str]:
    """Names of the installed MIDI output devices (a loopMIDI port shows up here)."""
    n = winmm.midiOutGetNumDevs()
    out = []
    for i in range(n):
        caps = MIDIOUTCAPS()
        if winmm.midiOutGetDevCapsW(i, ctypes.byref(caps), ctypes.sizeof(caps)) == 0:
            out.append(caps.szPname)
    return out


def find(name_part: str) -> int:
    """Device index whose name contains name_part (case-insensitive)."""
    for i, name in enumerate(ports()):
        if name_part.lower() in name.lower():
            return i
    raise LookupError(f"no MIDI out matching {name_part!r}; installed: {ports()}")


class MidiOut:
    def __init__(self, name_part: str = "loopMIDI") -> None:
        self.handle = wt.HANDLE()
        self.null = False
        try:
            dev = find(name_part)
        except LookupError:
            if os.environ.get("VSL_NULL_MIDI") == "1":
                self.null = True
                self.name = "<null>"
                print("[midi] no device matched, null sink active (timing test only)")
                return
            raise
        _err(winmm.midiOutOpen(ctypes.byref(self.handle), dev, 0, 0, CALLBACK_NULL))
        self.name = ports()[dev]

    # -- raw ---------------------------------------------------------------
    def _send(self, status: int, d1: int, d2: int = 0) -> None:
        if self.null:
            return
        msg = status | (d1 << 8) | (d2 << 16)
        winmm.midiOutShortMsg(self.handle, msg)

    # -- helpers -----------------------------------------------------------
    def note_on(self, ch: int, note: int, vel: int) -> None:
        self._send(0x90 | (ch & 0x0F), note & 0x7F, vel & 0x7F)

    def note_off(self, ch: int, note: int) -> None:
        self._send(0x80 | (ch & 0x0F), note & 0x7F, 0)

    def cc(self, ch: int, num: int, value: int) -> None:
        self._send(0xB0 | (ch & 0x0F), num & 0x7F, value & 0x7F)

    def program(self, ch: int, prog: int) -> None:
        self._send(0xC0 | (ch & 0x0F), prog & 0x7F)

    def pitch_bend(self, ch: int, value: int) -> None:
        """value: 0..16383, 8192 = centre."""
        v = max(0, min(16383, value))
        self._send(0xE0 | (ch & 0x0F), v & 0x7F, (v >> 7) & 0x7F)

    def all_notes_off(self, ch: int) -> None:
        self.cc(ch, 123, 0)

    def close(self) -> None:
        if self.null:
            return
        try:
            winmm.midiOutClose(self.handle)
        except Exception:
            pass


if __name__ == "__main__":
    print("MIDI outputs:")
    for i, p in enumerate(ports()):
        print(f"  {i}: {p}")
