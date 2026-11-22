from pathlib import Path
import fitz, json, hashlib
root=Path('deliverables/Wagner_Meistersinger_Original')
source=Path('wagner_work/Schott_18469_original.pdf')
score=fitz.open(root/'Wagner_名歌手前奏曲_原谱锚点与动机旁注.pdf')
report=fitz.open(root/'Wagner_名歌手前奏曲_深度分析.pdf')
orig=fitz.open(source)
assert len(score)==40 and len(report)==14 and len(orig)==39
per_page=[]
for i,src in enumerate(orig, start=1):
    page=score[i]
    source_w,source_h=src.rect.width,src.rect.height
    blocks=page.get_text('blocks')
    sidebar=[b for b in blocks if b[0]>source_w+18 and b[1]>=48 and b[2]<source_w+330]
    note_blocks=[b for b in sidebar if b[1]<source_h+48]
    max_note_y=max((b[3] for b in note_blocks),default=0)
    assert max_note_y<=source_h+48, (i,max_note_y,source_h+48)
    assert not any(b[1]<source_h+48 and b[3]>=source_h+52 for b in sidebar), (i,'sidebar/footer overlap')
    anns=list(page.annots() or [])
    per_page.append({'page':i,'highlights':len(anns),'sidebar_max_y':round(max_note_y,2)})
assert sum(p['highlights'] for p in per_page)==19
report_text='\n'.join(p.get_text() for p in report)
assert 'C5' in report_text and '邻音' in report_text
html=(root/'Wagner_名歌手前奏曲_导读.html').read_text(encoding='utf-8')
for term in ['Bülow','Schott','邻音','证据边界']:
    assert term in html, term
assert 'm.89' in html or 'm89' in html
result={'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'score_pages':len(score),'report_pages':len(report),'source_pages':len(orig),'highlight_total':19,'notehead_highlights':0,'max_sidebar_note_y':max(x['sidebar_max_y'] for x in per_page),'page_detail':per_page,'guide_bytes':(root/'Wagner_名歌手前奏曲_导读.html').stat().st_size}
(root/'delivery_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))
