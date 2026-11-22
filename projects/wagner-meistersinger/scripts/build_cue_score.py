from pathlib import Path
import sys, hashlib, json
import pymupdf as fitz
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import build_deliverables as b

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parent / 'deliverables/Wagner_Meistersinger_Original'
SRC = ROOT / 'Schott_18469_original.pdf'
FONT = b.FONT

# Source-page boxes are OCR candidates in top-left PDF points; they are not note locations.
CUES = {
  1: [([152.215,150.789,258.818,163.028], 'tempo', 'Opening tempo: “Sehr mässig bewegt.” This sets a broad, moving pace; it does not provide a metronome value.')],
  6: [([164.427,153.419,247.538,167.026], 'tempo', '“Ein wenig rallent.” followed by “Tempo” marks a local relaxation and return. The pair appears again lower on the page; treat it as phrase shaping, not a thematic label.'), ([284.087,151.164,316.179,167.172], 'tempo', 'Tempo restoration cue paired with the rallentando above.'), ([163.167,666.419,245.525,680.026], 'tempo', 'Second rallentando / tempo-return pair on this page.'), ([282.287,664.344,314.017,680.352], 'tempo', 'Second return-to-tempo cue.')],
  13: [([396.829,51.989,588.957,67.864], 'tempo', 'Exact wording crosswalk: Schott p.13 matches Bülow piano reduction m.89. In that reduction, the repeated-tone / neighbor cell recurs in m.91 and is transposed in m.93 and m.95. This links text and reduction, not individual original-score notes.'), ([398.209,665.609,589.224,681.484], 'tempo', 'The same tempo wording occurs again in a later system. Reduction evidence: m.89 and m.91 share the full pitch-rhythm cell; m.93 and m.95 repeat it a minor third higher.')],
  14: [([59.327,486.058,216.699,502.466], 'tempo', 'Main-tempo cue. Bülow m.97 has a nearby “Etwas mässiger … Hauptzeitmaass” instruction. This is a textual neighborhood only; do not transfer its key signature or notes to Schott.')],
  18: [([222.833,59.125,300.896,74.866], 'tempo', '“Noch bewegter” raises the motion level. The wording occurs twice on this page; the annotation tracks a pacing cue, not a new motive.'), ([221.753,890.004,298.137,905.746], 'tempo', 'Second “noch bewegter” cue on this page.')],
  19: [([70.73,43.562,246.549,60.371], 'tempo', 'Exact wording crosswalk: Schott p.19 matches Bülow m.122. The reduction’s m.121 retains the five-note neighbor tail C–D–C–B–C; m.150 repeats that tail one octave higher. This is a reduction-level local cell, not proof of original note identity.'), ([98.5,176.695,137.843,190.168], 'articulation', '“Sehr kurz” is printed as an articulation cue. Several short/staccato instructions occur on this page; compare their staff positions and durations before inferring which lines form independent counterpoint.'), ([605.211,174.005,627.287,187.478], 'articulation', '“Immer stacc.” is another explicit short-articulation cue. It supports a detached texture reading; note-level simultaneity is not inferred from OCR alone.'), ([176.98,242.395,203.207,255.868], 'articulation', 'A further “stacc.” cue on this page. The repeated articulation vocabulary is score evidence; exact note spans still require visual checking.')],
  27: [([546.02,714.471,623.128,727.278], 'tempo', '“Immer bewegter” specifies continuing animation. Bülow m.166 has an animato marking; this is a broad expressive parallel, not a verified bar-for-bar crosswalk.')],
  34: [([246.078,663.779,269.187,679.92], 'tempo', '“Sehr gewichtig” states the weight of this passage. Bülow m.196 says “pesante,” a semantic parallel only; do not infer identical pitches or orchestration.'), ([273.557,663.779,324.381,679.92], 'tempo', 'Completes the printed phrase “Sehr gewichtig.”'), ([320.178,120.467,361.994,134.875], 'dynamic', 'Representative repeated “immer ff” cue. Several similar dynamic marks appear across the page; this supports a sustained intensification, subject to visual review of each staff.'), ([242.978,871.427,283.134,885.835], 'dynamic', 'Another “Immer ff” cue near the end of the page.')],
}
COLORS = {'tempo': (0.96,0.75,0.12), 'articulation': (0.22,0.72,0.88), 'dynamic': (0.92,0.38,0.35)}

INTRO = [
 '底本：Schott 18469 原作管弦乐总谱，馆藏目录著录39页。以下保留全部39页；本PDF另加本说明页。',
 '荧光标记只落在可定位的原谱文字指示上：速度、发音和力度。没有把整行声部涂成动机。',
 '边栏严格区分两类材料：Schott 页码与文字是原谱扫描/OCR证据；音高与节奏例子来自 Bülow 钢琴缩编 MusicXML。二者只用可核对的速度文字建立有限交叉索引。',
 'Bülow m.89/91 的完整音高—节奏细胞相同；m.93/95 为同节奏移高小三度。m.121/150 只保留尾部邻音细胞。它们是缩编谱中的动机证据，不是原谱已核实的音符范围。',
 '黄色：速度文字；青色：短奏/断奏文字；红色：力度文字。点击标记可读批注。未作荧光标记的谱面仍为完整底本。',
 '图像模型未能视觉读取音符。本标注不声称完成逐音校勘，也不把缩编谱的小节号直接等同于 Schott 页码。'
]

def main():
    src = fitz.open(SRC)
    out = fitz.open()
    page = out.new_page(width=1000, height=900)
    page.insert_font(fontname='CN', fontfile=FONT)
    y = b.text_at(page, 48, 76, '瓦格纳《名歌手》前奏曲 · 原谱文字锚点与动机旁注', 900, 23)
    for line in INTRO:
        y = b.text_at(page, 50, y + 24, line, 890, 12)
    outline = [[1, '标注说明', 1]]
    for i, score_page in enumerate(src, start=1):
        w, h = score_page.rect.width, score_page.rect.height
        page = out.new_page(width=w + 330, height=h + 72)
        page.insert_font(fontname='CN', fontfile=FONT)
        page.show_pdf_page(fitz.Rect(14, 48, w + 14, h + 48), src, i - 1)
        page.draw_rect(fitz.Rect(w + 18, 48, w + 322, h + 48), fill=(0.97,0.975,0.98), color=None)
        x, width = w + 34, 278
        y = b.text_at(page, x, 74, f'Schott 第{i}页 · 原谱文字锚点', width, 12)
        items = CUES.get(i, [])
        if not items:
            y = b.text_at(page, x, y + 22, '本页没有加入动机音符高亮。', width, 10)
            y = b.text_at(page, x, y + 14, '总谱保持原样；请结合分析报告中的缩编谱动机例证。', width, 9.5)
        for j, (box, kind, note) in enumerate(items, start=1):
            color = COLORS[kind]
            label = {'tempo':'速度', 'articulation':'发音', 'dynamic':'力度'}[kind]
            y = b.text_at(page, x, y + 19, f'{j}. {label}', width, 10.5)
            y = b.text_at(page, x, y + 4, note, width, 9)
            x0,y0,x1,y1 = box
            rect = fitz.Rect(x0+14,y0+48,x1+14,y1+48)
            annot = page.add_highlight_annot(rect)
            annot.set_colors(stroke=color)
            annot.set_opacity(0.35)
            annot.set_info(title=f'Schott p.{i} · {label} OCR锚点', content=note + ' OCR坐标未经视觉校对；标记仅定位印刷文字，不定位音符。')
            annot.update()
        page.insert_text((20,h+63), f'Schott 18469 | original page {i}/39 | text cues only', fontsize=8)
        if items:
            outline.append([1, f'Schott 第{i}页 · {len(items)}处文字锚点', i+1])
    out.set_toc(outline)
    out.set_metadata({'title':'名歌手前奏曲：原谱文字锚点与缩编谱动机旁注','author':'Music analysis','subject':'Schott 18469 score text cues and Bülow reduction cell audit'})
    out.subset_fonts()
    target = OUT / 'Wagner_名歌手前奏曲_原谱锚点与动机旁注.pdf'
    out.save(target, garbage=4, deflate=True)
    source_sha = hashlib.sha256(SRC.read_bytes()).hexdigest()
    counts = [len(list(p.annots() or [])) for p in out]
    result = {'source_sha256': source_sha, 'source_pages': len(src), 'output_pages': len(out), 'highlight_count': sum(counts), 'annotated_source_pages': [i for i,c in enumerate(counts[1:],1) if c], 'per_source_page': counts[1:], 'image_note_proofreading': False, 'note_highlights': 0}
    (OUT / 'cue_score_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    print(target)
    print(json.dumps(result,ensure_ascii=False))

if __name__ == '__main__':
    main()
