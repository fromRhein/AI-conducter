from pathlib import Path
import sys,json,re,hashlib
import pymupdf as fitz
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
import build_deliverables as b
from reportlab.platypus import SimpleDocTemplate,Paragraph,PageBreak,Image
BASE=Path(__file__).resolve().parent
OUT=BASE.parent/'deliverables/Wagner_Meistersinger_Original';OUT.mkdir(parents=True,exist_ok=True)
SRC=BASE/'Schott_18469_original.pdf'
FONT=b.FONT

def bands(p):
 found=[]
 for w in p.get_text('words'):
  if w[0]>p.rect.width*.3:continue
  t=re.sub(r'[^a-z0-9]','',w[4].lower());kind=None
  if t in ['vl1','vli','vi1','v11','violinen','vc','cb','br']:kind='theme'
  if t in ['grfl','fl','hb','kl','fg','hr','pos','tr']:kind='orchestration'
  if kind and not any(abs(w[1]-a[0][1])<20 for a in found):found.append((w,kind))
 return found[:5]

def score():
 notes=json.loads((BASE/'original_page_notes.json').read_text(encoding='utf-8-sig'))
 if isinstance(notes,dict):notes=notes['pages']
 assert len(notes)==39
 idx={int(n['page']):n for n in notes};src=fitz.open(SRC);d=fitz.open();audit=[]
 p=d.new_page(width=1000,height=900);p.insert_font(fontname='CN',fontfile=FONT)
 y=b.text_at(p,50,80,'瓦格纳《纽伦堡的名歌手》第一幕前奏曲',900,25)
 y=b.text_at(p,50,y+25,'原作管弦乐总谱 · 中文分析注释版',900,22)
 paras=['底本：B. Schott’s Söhne，版号18469。罗切斯特大学 Sibley 音乐图书馆馆藏，目录标注1870年。完整39页；加本说明页后共40页。','“原版”指原作管弦乐编制的历史出版总谱，不是手稿、首版认证或现代批判校订版。已弃用先前的Hoffmann缩编谱。','黄色与青色高亮是声部阅读带，帮助比较弦乐与管乐层次；并非逐音主题识别。原谱音符完整保留。PDF注释可在阅读器中隐藏。','每页旁注区分谱面可读文字与分析性阅读建议。未证实的页首小节号不补造；按Schott页码定位。','音符级材料示例来自另行标明的Bülow钢琴缩编电子谱，作为和声与主题的辅助证据，不据此推定原管弦乐声部归属。','完成了文本坐标与文件完整性检查，未完成原谱逐音视觉校勘。关于全曲调性、主题关系与作曲技术，详见配套分析报告。','来源：https://hdl.handle.net/1802/25060']
 for text in paras:y=b.text_at(p,50,y+25,text,890,13)
 for i,sp in enumerate(src):
  w,h=sp.rect.width,sp.rect.height;p=d.new_page(width=w+310,height=h+72);p.insert_font(fontname='CN',fontfile=FONT)
  p.show_pdf_page(fitz.Rect(14,48,w+14,h+48),src,i);b.text_at(p,20,28,'WAGNER · DIE MEISTERSINGER · 原作总谱',w,13)
  x=w+32;ww=252;p.draw_rect(fitz.Rect(x-9,48,w+300,h+48),fill=(.96,.97,.98),color=None)
  info=idx[i+1];y=b.text_at(p,x,74,f'Schott 第{i+1}页',ww,12);y=b.text_at(p,x,y+12,info['title'],ww,14)
  for n in info['notes']:
   y+=18;p.draw_rect(fitz.Rect(x,y-10,x+4,y+4),fill=b.PALETTE.get(n.get('kind'),b.PALETTE['form']),color=None)
   y=b.text_at(p,x+12,y,n['title'],ww-12,11);y=b.text_at(p,x,y+5,n['text'],ww,9.5)
  marks=0
  from fix_highlight_alignment import marks as aligned_marks
  for entry in aligned_marks(sp):
   a=p.add_highlight_annot(fitz.Quad(entry['quad']));a.set_colors(stroke=b.PALETTE[entry['kind']]);a.set_opacity(.18)
   a.set_info(title='五线谱定位的声部观察带',content='根据五条谱线像素位置与局部倾斜拟合定位；不是逐音主题标签。');a.update();marks+=1
  assert y<h+20,(i+1,y,h)
  audit.append({'page':i+1,'notes':len(info['notes']),'highlights':marks,'last_y':y,'height':h+72})
  p.insert_text((20,h+63),f'Schott 18469 | source {i+1}/39 | original orchestration',fontsize=8)
 d.set_toc([[1,'版本与阅读说明',1]]+[[1,f'Schott 第{n}页',n+1] for n in [1,7,13,19,25,31,37]])
 d.subset_fonts();d.save(OUT/'Wagner_名歌手前奏曲_原作注释总谱.pdf',garbage=4,deflate=True)
 (OUT/'annotation_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf8')

def report():
 text=(BASE/'original_analysis.md').read_text(encoding='utf-8-sig')
 text=re.sub(r'\]\(<([^>]+)>\)',lambda m:'](<'+(BASE/m[1]).resolve().as_posix()+'>)',text)
 (OUT/'Wagner_名歌手前奏曲_深度分析.md').write_text(text,encoding='utf8');flow=b.md_flow(text);src=fitz.open(SRC)
 flow.extend([PageBreak(),Paragraph('原谱阅读窗口',b.styles['CNH1']),Paragraph('以下保留原作谱面上下文。速度、发音与力度文字锚点及其缩编谱证据见配套旁注总谱。',b.styles['CNBody'])])
 for pn in [1,13,19,27,35,39]:
  p=src[pn-1];file=OUT/f'score_page_{pn:02}.png';p.get_pixmap(matrix=fitz.Matrix(1.5,1.5)).save(file)
  img=Image(str(file));rat=min(475/img.imageWidth,630/img.imageHeight);img.drawWidth=img.imageWidth*rat;img.drawHeight=img.imageHeight*rat
  flow.extend([Paragraph(f'Schott 原谱第{pn}页',b.styles['CNH2']),img,PageBreak()])
 def footer(c,d):
  c.setFont('Chinese',8);c.drawString(60,28,'WAGNER · WWV 96 · 原作总谱分析');c.drawRightString(535,28,str(d.page))
 SimpleDocTemplate(str(OUT/'Wagner_名歌手前奏曲_深度分析.pdf'),pagesize=(595.28,841.89),leftMargin=60,rightMargin=60,topMargin=45,bottomMargin=50).build(flow,onFirstPage=footer,onLaterPages=footer)

def verify():
 import numpy as np
 s=fitz.open(SRC);d=fitz.open(OUT/'Wagner_名歌手前奏曲_原谱锚点与动机旁注.pdf');assert len(d)==40;diff=[];counts=[];max_y=0
 for i,p in enumerate(s):
  target=d[i+1];annots=list(target.annots() or []);counts.append(len(annots))
  for a in annots:
   r=a.rect
   assert r.width < p.rect.width*.5, ('broad highlight',i+1,r.width)
   assert r.x0>=14 and r.x1<=p.rect.width+14 and r.y0>=48 and r.y1<=p.rect.height+48
  blocks=target.get_text('blocks');max_y=max(max_y,max((b0[3] for b0 in blocks),default=0))
  a0=p.get_pixmap(matrix=fitz.Matrix(.5,.5),colorspace=fitz.csGRAY,annots=False)
  z=target.get_pixmap(matrix=fitz.Matrix(.5,.5),colorspace=fitz.csGRAY,clip=fitz.Rect(14,48,p.rect.width+14,p.rect.height+48),annots=False)
  assert (a0.width,a0.height)==(z.width,z.height)
  diff.append(float(np.abs(np.frombuffer(a0.samples,np.uint8).astype(int)-np.frombuffer(z.samples,np.uint8).astype(int)).mean()))
 r=fitz.open(OUT/'Wagner_名歌手前奏曲_深度分析.pdf')
 result={'source_sha256':hashlib.sha256(SRC.read_bytes()).hexdigest(),'source_pages':len(s),'annotated_pdf_pages':len(d),'report_pages':len(r),'text_highlights':sum(counts),'note_highlights':0,'pages_with_cues':[i+1 for i,c in enumerate(counts) if c],'max_mean_render_difference_without_annotations':max(diff),'sidebar_max_y':max_y,'visual_note_proofreading':False}
 (OUT/'cue_score_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8');print(result)
if __name__=='__main__':score();report();verify()
