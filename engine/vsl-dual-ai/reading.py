"""Read the score before playing it.

Stage 1 of the run: turn the MIDI into a digest a musician would actually look
at (phrases, register, density, clashes, cadence candidates), ask each model for
a written interpretation, and lay it out as a PDF. The text then travels with
every later request, so the bar-by-bar decisions are made "having read the
piece", not fresh each bar.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass

FONT_CANDIDATES = [
    ("MSYH", r"C:\Windows\Fonts\msyh.ttc", 0),
    ("MSYHBD", r"C:\Windows\Fonts\msyhbd.ttc", 0),
    ("SIMSUN", r"C:\Windows\Fonts\simsun.ttc", 0),
]

NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def pname(n: int) -> str:
    return f"{NAMES[n % 12]}{n // 12 - 1}"


# ---------------------------------------------------------------- digest

INTERVALS = {0: "同度", 1: "小二度", 2: "大二度", 3: "小三度", 4: "大三度", 5: "纯四度",
             6: "三全音", 7: "纯五度", 8: "小六度", 9: "大六度", 10: "小七度", 11: "大七度"}


def _chord_of(pcs: set[int]) -> str:
    if not pcs:
        return "-"
    if len(pcs) < 3:                      # two notes: name the interval, not a chord
        root = min(pcs)
        other = max(pcs)
        return f"{NAMES[root % 12]}+{INTERVALS[(other - root) % 12]}"
    root = min(pcs)
    rel = {(p - root) % 12 for p in pcs}
    if {0, 4, 7, 11} <= rel:
        return f"{NAMES[root % 12]}maj7"
    if {0, 4, 7, 10} <= rel:
        return f"{NAMES[root % 12]}7"
    if {0, 3, 7, 10} <= rel:
        return f"{NAMES[root % 12]}m7"
    if {0, 4, 7} <= rel:
        return f"{NAMES[root % 12]}"
    if {0, 3, 7} <= rel:
        return f"{NAMES[root % 12]}m"
    if {0, 3, 6} <= rel:
        return f"{NAMES[root % 12]}dim"
    if {0, 2, 7} <= rel:
        return f"{NAMES[root % 12]}sus2"
    if {0, 5, 7} <= rel:
        return f"{NAMES[root % 12]}sus4"
    return f"{NAMES[root % 12]}?"


def digest(notes_a, notes_b, bpb: int, bpm: float) -> dict:
    bars = int(max([n.beat for n in list(notes_a) + list(notes_b)] or [0]) // bpb) + 1
    per_bar = []
    for bar in range(bars):
        lo, hi = bar * bpb, (bar + 1) * bpb
        a = [n for n in notes_a if lo <= n.beat < hi]
        b = [n for n in notes_b if lo <= n.beat < hi]
        pcs = {(n.note % 12) for n in a + b}
        onsets_a = {round(n.beat - bar * bpb, 2) for n in a}
        onsets_b = {round(n.beat - bar * bpb, 2) for n in b}
        per_bar.append({
            "bar": bar + 1,
            "a": len(a), "b": len(b),
            "range_a": (min((n.note for n in a), default=0), max((n.note for n in a), default=0)),
            "range_b": (min((n.note for n in b), default=0), max((n.note for n in b), default=0)),
            "vel_a": round(sum(n.vel for n in a) / len(a)) if a else 0,
            "vel_b": round(sum(n.vel for n in b) / len(b)) if b else 0,
            "chord": _chord_of(pcs) if pcs else "-",
            "both": len(onsets_a & onsets_b),
            "long_a": max((n.dur for n in a), default=0.0),
            "long_b": max((n.dur for n in b), default=0.0),
        })

    # phrase map: group consecutive bars that hold the same harmony; a bar that
    # changes chord on its own is folded into its neighbour (one-bar phrases are
    # not phrases).
    spans: list[list[int]] = []
    for row in per_bar:
        if spans and spans[-1][2] == row["chord"]:
            spans[-1][1] = row["bar"]
        else:
            spans.append([row["bar"], row["bar"], row["chord"]])
    merged: list[tuple[int, int]] = []
    for lo, hi, _ in spans:
        if merged and hi - lo == 0:
            merged[-1] = (merged[-1][0], hi)
        else:
            merged.append((lo, hi))
    phrases = merged

    # cadence candidates: a bar where both voices hold a note past the bar line
    cadence = [r["bar"] for r in per_bar
               if r["long_a"] > bpb * 0.6 and r["long_b"] > bpb * 0.6]
    clashes = [c for c in cadence]
    return {
        "bpm": bpm, "beats_per_bar": bpb, "bars": bars,
        "sec_per_bar": round(bpb * 60.0 / bpm, 2),
        "per_bar": per_bar,
        "phrases": phrases,
        "cadence_candidates": clashes,
        "range_a": (min((n.note for n in notes_a), default=0), max((n.note for n in notes_a), default=0)),
        "range_b": (min((n.note for n in notes_b), default=0), max((n.note for n in notes_b), default=0)),
        "notes_a": len(notes_a), "notes_b": len(notes_b),
    }


def brief_text(d: dict, who: str) -> str:
    lines = [
        f"Piece: {d['bars']} bars, {d['beats_per_bar']}/4, {d['bpm']:.0f} BPM "
        f"({d['sec_per_bar']} s per bar).",
    ]
    mine_rng = d["range_a"] if who == "A" else d["range_b"]
    theirs_rng = d["range_b"] if who == "A" else d["range_a"]
    lines.append(f"Your voice: {d['notes_a'] if who == 'A' else d['notes_b']} notes, "
                 f"range {pname(mine_rng[0])}-{pname(mine_rng[1])}.")
    lines.append(f"Partner: {d['notes_b'] if who == 'A' else d['notes_a']} notes, "
                 f"range {pname(theirs_rng[0])}-{pname(theirs_rng[1])}.")
    lines.append("")
    lines.append("Bar-by-bar (bar | your notes + range | partner notes + range | "
                 "your vel | partner vel | harmony | shared onsets | longest note):")
    for r in d["per_bar"]:
        mine, theirs = (r["a"], r["b"]) if who == "A" else (r["b"], r["a"])
        mv, tv = (r["vel_a"], r["vel_b"]) if who == "A" else (r["vel_b"], r["vel_a"])
        lo_m, hi_m = r["range_a"] if who == "A" else r["range_b"]
        lo_t, hi_t = r["range_b"] if who == "A" else r["range_a"]
        rng = f"{pname(lo_m)}-{pname(hi_m)}" if mine else "-"
        rng_t = f"{pname(lo_t)}-{pname(hi_t)}" if theirs else "-"
        long_m = r["long_a"] if who == "A" else r["long_b"]
        lines.append(
            f"  {r['bar']:>3} | {mine:>2} {rng:<9} | {theirs:>2} {rng_t:<9} | "
            f"{mv:>3} | {tv:>3} | {r['chord']:<5} | {r['both']} | {long_m:.1f}"
        )
    lines += [
        "",
        "Phrase map (bar spans where the harmony holds): " +
        ", ".join(f"{a}-{b}" for a, b in d["phrases"]),
        "Bars where both voices hold through the bar line (phrase-ending candidates): " +
        (", ".join(str(b) for b in d["cadence_candidates"]) or "none"),
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------- the ask

READ_SYSTEM = """You are {name}, one half of a two-piano duo about to play this piece
on a VSL Steinway D-274. Your partner is {partner}. Before touching the keyboard you
read the score and write down your interpretation, in Chinese, for yourself.

Write it as if marking up the part: no plot summaries, no praise. Concrete decisions.
Sections to write (use these exact headings):
## 段落与呼吸
## 速度走向
## 力度曲线
## 踏板策略
## 我的声部怎么走
## 和搭档的交接
## 三处我最担心的地方
Keep it under 900 Chinese characters. Numbers where numbers help (bar numbers,
BPM, dB, ms). This document will be quoted back to you at every bar you play, so
write the sentences you will actually want to re-read mid-performance."""


def ask_reading(model, brief: str, partner: str) -> str:
    """Return the model's written interpretation, or '' when it has no key."""
    if not hasattr(model, "ask_text"):
        return ""
    system = READ_SYSTEM.format(name=model.cfg.name, partner=partner)
    return model.ask_text(system, brief) or ""


def fallback_reading(d: dict, who: str) -> str:
    """Deterministic interpretation so the PDF stage works with no API key."""
    mine = "A" if who == "A" else "B"
    rng = d["range_a"] if mine == "A" else d["range_b"]
    densest = max(d["per_bar"], key=lambda r: r["a"] if mine == "A" else r["b"])
    lightest = min(d["per_bar"], key=lambda r: r["a"] if mine == "A" else r["b"])
    phrases = "、".join(f"{a}–{b}" for a, b in d["phrases"][:6])
    whole = len(d["phrases"]) == 1 and d["phrases"][0][0] == 1 and d["phrases"][0][1] == d["bars"]
    phrase_sentence = (f"和声每小节都在换，抓不到成段的和声块，乐句只能靠呼吸和力度切。"
                       if whole else f"和声把乐句分成 {phrases}。")
    cad = "、".join(str(b) for b in d["cadence_candidates"][:6])
    worry_cad = (f"{cad} 小节双方都拖长音，容易抢气口。" if cad
                 else "没有双方同时拖长音的落点，交接只能靠力度：谁先退，另一个就接。")
    dense_bar = densest["bar"]
    light_bar = lightest["bar"]
    return f"""## 段落与呼吸
全曲 {d['bars']} 小节，{phrase_sentence}
我的呼吸放在每一段最后一拍的后半，不在 {light_bar} 小节这种音稀的空隙里抢气。

## 速度走向
以 {d['bpm']:.0f} BPM 为轴：段落起头 −2%，到乐句尾 +1.5% 收住；
{d['bars']} 小节最后一个和弦前留 40 ms 的迟滞，然后交给搭档。

## 力度曲线
我的音域 {pname(rng[0])}–{pname(rng[1])}，平均力度控在 70–85。
密集的 {dense_bar} 小节压到 0.9 倍避免糊成一片，稀疏处抬到 1.15 倍填满。

## 踏板策略
每小节第一拍踩满 CC64，第二、三拍之间放一次；换和声时先放后踩，间隔 40 ms。
乐句尾不踩，让余韵自己走。

## 我的声部怎么走
外声部（{pname(rng[1])} 附近）往前带 5–8 ms，内声部贴着格点。
超过 1.5 拍的长音，在起音后 20 ms 补一点力度，模拟钢琴的自然衰减。

## 和搭档的交接
听对方的平均力度：超过 85 我退到 0.85 倍；低于 65 我接过来。
对方把 tempo 推到 1.03 以上，我只跟一半，不抢主导。

## 三处我最担心的地方
1. {worry_cad}
2. {dense_bar} 小节音符最密，踏板必须短，一糊就全糊。
3. {phrases.split('、')[1] if '、' in phrases else phrases} 这段交接时，两边速度最容易分叉。"""


# ---------------------------------------------------------------- PDF

def _clean(md: str) -> str:
    md = re.sub(r"\*\*(.+?)\*\*", r"\1", md)
    md = re.sub(r"`([^`]+)`", r"\1", md)
    return md.strip()


def _appendix(d: dict, who: str, font: str):
    """The bar table the model was looking at, for reference while playing."""
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import Paragraph, Table, TableStyle

    cell = ParagraphStyle("cell", fontName=font, fontSize=7.6, leading=9.6, wordWrap="CJK")
    head = ParagraphStyle("cellh", fontName=font, fontSize=7.8, leading=10, wordWrap="CJK")

    rows = [[Paragraph(h, head) for h in
             ("小节", "本声部音域", "音符", "对方音符", "力度", "和声", "同起音")]]
    for r in d["per_bar"]:
        mine = (r["a"], f"{pname(r['range_a'][0])}-{pname(r['range_a'][1])}") if who == "A" \
            else (r["b"], f"{pname(r['range_b'][0])}-{pname(r['range_b'][1])}")
        theirs = r["b"] if who == "A" else r["a"]
        vel = r["vel_a"] if who == "A" else r["vel_b"]
        rows.append([Paragraph(str(x), cell) for x in (
            r["bar"], mine[1] if mine[0] else "-", mine[0], theirs, vel, r["chord"], r["both"])])
    tbl = Table(rows, colWidths=[34, 70, 34, 44, 34, 46, 40], repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")),
        ("LINEBELOW", (0, 0), (-1, 0), 0.6, colors.HexColor("#999999")),
        ("LINEBELOW", (0, 1), (-1, -1), 0.2, colors.HexColor("#cccccc")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
    ]))
    return tbl


def to_pdf(text: str, path: str, title: str, subtitle: str = "",
           d: dict | None = None, who: str = "A") -> str:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import (PageBreak, Paragraph, SimpleDocTemplate, Spacer)

    font, bold = "Helvetica", "Helvetica-Bold"
    for name, fp, idx in FONT_CANDIDATES:
        if os.path.exists(fp):
            try:
                pdfmetrics.registerFont(TTFont(name, fp, subfontIndex=idx))
                if font == "Helvetica":
                    font = name
                elif bold == "Helvetica-Bold" and name != font:
                    bold = name
            except Exception:
                continue

    body = ParagraphStyle("body", fontName=font, fontSize=10.5, leading=17,
                          spaceAfter=6, wordWrap="CJK")
    head = ParagraphStyle("head", fontName=bold, fontSize=13, leading=20,
                          spaceBefore=10, spaceAfter=4, wordWrap="CJK")
    h1 = ParagraphStyle("h1", fontName=bold, fontSize=18, leading=24,
                        spaceAfter=4, wordWrap="CJK")
    sub = ParagraphStyle("sub", fontName=font, fontSize=9.5, leading=14,
                         textColor="#555555", spaceAfter=12, wordWrap="CJK")

    doc = SimpleDocTemplate(path, pagesize=A4,
                            leftMargin=22 * mm, rightMargin=22 * mm,
                            topMargin=20 * mm, bottomMargin=18 * mm,
                            title=title, author="two-player duo")
    flow = [Paragraph(title, h1)]
    if subtitle:
        flow.append(Paragraph(subtitle, sub))
    for raw in _clean(text).splitlines():
        line = raw.rstrip()
        if not line:
            flow.append(Spacer(1, 4))
            continue
        if line.startswith("##"):
            flow.append(Paragraph(line.lstrip("#").strip(), head))
        elif line.startswith("#"):
            flow.append(Paragraph(line.lstrip("#").strip(), h1))
        else:
            flow.append(Paragraph(line.replace("&", "&amp;").replace("<", "&lt;"), body))
    if d is not None:
        flow.append(PageBreak())
        flow.append(Paragraph("附录 · 小节表（写这份笔记时看到的原始数据）", head))
        flow.append(Spacer(1, 3))
        flow.append(_appendix(d, who, font))
    doc.build(flow)
    return path


def save(text: str, out_dir: str, tag: str, meta: dict,
         d: dict | None = None) -> tuple[str, str]:
    os.makedirs(out_dir, exist_ok=True)
    md_path = os.path.join(out_dir, f"reading_{tag}.md")
    pdf_path = os.path.join(out_dir, f"reading_{tag}.pdf")
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write(text)
    subtitle = (f"{meta.get('score', '')} · {meta.get('bars', '')} bars · "
                f"{meta.get('bpm', '')} BPM · 演奏前的谱面理解")
    to_pdf(text, pdf_path, f"读谱笔记 · Player {tag}", subtitle, d=d, who=tag)
    return md_path, pdf_path


if __name__ == "__main__":
    import sys
    from score import load_track

    path_a, path_b = (sys.argv[1], sys.argv[2]) if len(sys.argv) > 2 else ("example_a.mid", "example_b.mid")
    na, nb = load_track(path_a), load_track(path_b)
    d = digest(na, nb, 4, 84.0)
    print(brief_text(d, "A")[:1200])
    text = fallback_reading(d, "A")
    md, pdf = save(text, ".", "A", {"score": f"{path_a}+{path_b}", "bars": d["bars"], "bpm": 84})
    print("wrote", md, pdf)
