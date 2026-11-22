from pathlib import Path
import re, json, html, math
import pymupdf as fitz
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image, KeepTogether
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_LEFT

BASE=Path(__file__).resolve().parent
OUT=BASE/'deliverables';OUT.mkdir(exist_ok=True)
ASSETS=OUT/'assets';ASSETS.mkdir(exist_ok=True)
FONT='C:/Windows/Fonts/simhei.ttf'
pdfmetrics.registerFont(TTFont('Chinese',FONT))
SOURCE=Path('D:/scores/brahms/Brahms_-_Symphony_No.4_in_E_minor,_Op.98.pdf')
TITLES={1:'第一乐章 · 材料的持续生成',2:'第二乐章 · 调式与歌唱',3:'第三乐章 · 节奏与明度',4:'第四乐章 · 约束中的变形'}
PALETTE={'theme':(0.98,0.85,0.22),'orchestration':(0.30,0.82,0.91),'harmony':(0.51,0.77,0.45),'form':(0.88,0.48,0.59)}
DARK=(0.13,0.20,0.27)
CJK=fitz.Font(fontfile=FONT)

def wrap_text(text,width,size):
 lines=[]
 for para in text.split('\n'):
  current=''
  for char in para:
   if CJK.text_length(current+char,fontsize=size)>width:
    lines.append(current);current=char
   else:current+=char
  lines.append(current)
 return lines

def text_at(p,x,y,text,width,size=10,color=DARK,leading=None):
 leading=leading or size*1.55
 for line in wrap_text(text,width,size):
  p.insert_text((x,y),line,fontname='CN',fontsize=size,color=color)
  y+=leading
 return y

def rows(p,kind):
 found=[]
 for w in p.get_text('words'):
  if w[0]>p.rect.width*.32:continue
  s=w[4].lower().replace(' ','').replace(':','.').replace('!','l')
  ok=bool(re.search(r'^[1tlf][.\-]?vio',s)) if kind=='strings' else s in ['fl.','fl','gr.fl.','gr.fl','gr.fi.']
  if ok and not any(abs((w[1]+w[3])/2-y)<28 for y,_ in found):
   found.append(((w[1]+w[3])/2,w[2]))
 return sorted(found)[:3]

def load_index():
 path=BASE/'reports/pdf_page_starts.json'
 if not path.exists():path=BASE/'work/provisional_page_starts.json'
 data=json.loads(path.read_text(encoding='utf-8-sig'))
 if isinstance(data,dict):data=data.get('pages',data.get('index',[]))
 return {int(p['page']):p for p in data}

def annotated_score():
 source=fitz.open(SOURCE); doc=fitz.open()
 events=json.loads((BASE/'annotations.json').read_text(encoding='utf-8'))
 index=load_index();audit=[]
 cover=doc.new_page(width=980,height=864);cover.insert_font(fontname='CN',fontfile=FONT)
 cover.draw_rect(fitz.Rect(0,0,980,160),fill=(.12,.20,.26),color=None)
 text_at(cover,50,67,'BRAHMS  /  SYMPHONY No.4',870,24,(1,1,1))
 text_at(cover,50,118,'勃拉姆斯《第四交响曲》全曲注释总谱',870,25,(1,1,1))
 y=text_at(cover,52,205,'阅读方式',870,19)
 intro=['完整保留原始98页总谱；每页右侧附中文分析。原谱页在本文件中顺延1页。',
 '曲式与和声解释请配合《全曲深度分析》阅读。此总谱侧重演奏中可追踪的材料与声部。',
 '黄色：弦乐观察带。青色：长笛／木管观察带。高亮覆盖声部区域，并非逐音动机标签。',
 '旁注中的绿色标识和声问题，玫红标识结构问题。小节范围限定论述对象。',
 '高亮位置由谱面文字坐标辅助定位，保留原谱全部音符；遇到识别不足的页面不强行划线。',
 '原印页247—344，对应原PDF页1—98。四乐章的原PDF起点为1、30、42、68。',
 '第一乐章采用弱起不计入完整小节的编号；电子谱节点序号与此相差1。',
 '页首小节号识别不足时标为“跨页参考段／页界待核”，其旁注讨论相邻数页共同覆盖的段落。']
 for para in intro:y=text_at(cover,52,y+18,para,865,12)
 y=text_at(cover,52,y+35,'书签导航',865,18)
 for m,pn in [(1,1),(2,30),(3,42),(4,68)]:y=text_at(cover,52,y+12,f'{TITLES[m]}  |  原PDF {pn}页 / 本文件 {pn+1}页',865,13)
 toc=[[1,'阅读说明',1]]
 for i,src in enumerate(source):
  n=i+1; info=index[n];m=int(info['movement']);start=info.get('start')
  nxt=index.get(n+1,{});end=(nxt.get('start') or 0)-1 if nxt.get('movement')==m and nxt.get('start') else {1:440,2:118,3:357,4:311}[m]
  if start is None:start=1;end={1:440,2:118,3:357,4:311}[m]
  w,h=src.rect.width,src.rect.height
  p=doc.new_page(width=w+310,height=h+72);p.insert_font(fontname='CN',fontfile=FONT)
  p.show_pdf_page(fitz.Rect(14,48,w+14,h+48),source,i)
  text_at(p,22,27,TITLES[m],w-20,15)
  sx=w+34;sw=252
  p.draw_rect(fitz.Rect(sx-10,48,w+298,h+47),fill=(.969,.973,.976),color=None)
  label=f'原PDF {n:02d}  ·  原印 {n+246}'
  y=text_at(p,sx,72,label,sw,11)
  conf=info.get('confidence','')
  uncertain=conf not in ['verified','ocr'] or (nxt.get('movement')==m and nxt.get('confidence') not in ['verified','ocr'])
  if uncertain and 'lower' in info:
   start=info['lower'];end=info['upper'];conf='inferred'
  rlabel=f'本页阅读范围：m{start}—{end}'
  if uncertain:rlabel=f'跨页参考段：m{start}—{end}（页界待核）'
  y=text_at(p,sx,y+10,rlabel,sw,11)
  selected=[a for a in events if a['movement']==m and a['end']>=start and a['start']<=end]
  if not selected:selected=[min((a for a in events if a['movement']==m),key=lambda a:abs(a['start']-start))]
  selected=selected[:4]
  for a in selected:
   col=PALETTE[a.get('kind','theme')]
   y+=20
   p.draw_rect(fitz.Rect(sx,y-10,sx+5,y+6),fill=col,color=None)
   y=text_at(p,sx+13,y,a['title'],sw-13,12)
   y=text_at(p,sx,y+6,f"m{a['start']}—{a['end']}",sw,9,(.42,.47,.52))
   y=text_at(p,sx,y+7,a['text'],sw,10)
  y=max(y+28,h-135)
  if y<h-58:
   text_at(p,sx,y,'读谱提示',sw,10,(.42,.47,.52))
   text_at(p,sx,y+20,'把上声部旋律、内声部节奏和低音分开追踪，再听它们如何同时改变。',sw,9,(.42,.47,.52))
  count=0
  for kind,color in [('strings',PALETTE['theme']),('winds',PALETTE['orchestration'])]:
   for cy,right in rows(src,kind):
    rect=fitz.Rect(max(right+7,75)+14,cy-11+48,w-25+14,cy+11+48)
    ann=p.add_highlight_annot(rect)
    ann.set_colors(stroke=color)
    ann.set_opacity(.23)
    ann.set_info(title='声部观察带',content=('弦乐' if kind=='strings' else '木管')+'观察带；具体小节与分析见右侧旁注。该带不表示逐音动机归属。')
    ann.update()
    count+=1
  p.insert_text((22,h+64),f'Op.98 | {m} | Source PDF {n}/98 | Study edition',fontname='helv',fontsize=8,color=(.4,.45,.5))
  audit.append({'source_page':n,'movement':m,'start':start,'end':end,'confidence':conf,'highlight_bands':count,'notes':len(selected),'last_note_y':y,'page_height':h+72})
  if n in [1,30,42,68]:toc.append([1,TITLES[m],n+1])
 doc.set_toc(toc);doc.set_metadata({'title':'勃拉姆斯第四交响曲：全曲注释总谱','author':'音乐分析研究版','subject':'原谱98页与中文旁注；高亮为声部阅读带'})
 doc.subset_fonts();dest=OUT/'Brahms_Op98_全曲注释总谱.pdf';doc.save(dest,garbage=4,deflate=True)
 (OUT/'annotation_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf8')
 doc.close();source.close();return dest

styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='CNBody',fontName='Chinese',fontSize=10.2,leading=17,wordWrap='CJK',spaceAfter=8,textColor=colors.HexColor('#243643')))
styles.add(ParagraphStyle(name='CNH1',parent=styles['CNBody'],fontSize=22,leading=30,spaceBefore=15,spaceAfter=18,textColor=colors.HexColor('#142b3c')))
styles.add(ParagraphStyle(name='CNH2',parent=styles['CNBody'],fontSize=15,leading=22,spaceBefore=16,spaceAfter=9,textColor=colors.HexColor('#176e7d')))
styles.add(ParagraphStyle(name='CNH3',parent=styles['CNBody'],fontSize=12,leading=19,spaceBefore=12,spaceAfter=7))
styles.add(ParagraphStyle(name='CNCell',parent=styles['CNBody'],fontSize=8.1,leading=12,spaceAfter=1))
styles.add(ParagraphStyle(name='CNCaption',parent=styles['CNBody'],fontSize=9,leading=14,textColor=colors.HexColor('#536775')))

def rich(text):
 text=html.escape(text)
 text=re.sub(r'\*\*(.*?)\*\*',r'<b>\1</b>',text)
 text=re.sub(r'`([^`]+)`',r'\1',text)
 text=re.sub(r'\[([^]]+)\]\(([^)]+)\)',r'\1（\2）',text)
 return text

def md_flow(md):
 lines=md.splitlines();flow=[];i=0
 while i<len(lines):
  line=lines[i].strip()
  if not line:i+=1;continue
  if line.startswith('|'):
   table=[]
   while i<len(lines) and lines[i].strip().startswith('|'):
    cells=[c.strip() for c in lines[i].strip().strip('|').split('|')]
    if not all(re.fullmatch(r'[:\- ]+',c or '-') for c in cells):table.append(cells)
    i+=1
   cols=max(map(len,table));widths=[475/cols]*cols
   if cols==4:widths=[65,107,153,150]
   elif cols==3:widths=[88,125,262]
   elif cols==5:widths=[43,63,116,123,130]
   data=[[Paragraph(rich(c),styles['CNCell']) for c in row+['']*(cols-len(row))] for row in table]
   t=Table(data,colWidths=widths,repeatRows=1,hAlign='LEFT')
   t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e0edf0')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f4f7f8')]),('VALIGN',(0,0),(-1,-1),'TOP'),('GRID',(0,0),(-1,-1),.3,colors.HexColor('#d0dbe0')),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
   flow.extend([t,Spacer(1,12)]);continue
  if line.startswith('```'):
   code=[];i+=1
   while i<len(lines) and not lines[i].startswith('```'):code.append(lines[i]);i+=1
   flow.append(Paragraph('<br/>'.join(rich(x) for x in code),styles['CNCaption']));i+=1;continue
  head=re.match(r'^(#{1,6})\s+(.*)',line)
  if head:
   style='CNH1' if len(head[1])==1 else 'CNH2' if len(head[1])==2 else 'CNH3'
   flow.append(Paragraph(rich(head[2]),styles[style]));i+=1;continue
  if re.fullmatch(r'[-*_]{3,}',line):i+=1;continue
  flow.append(Paragraph(rich(line.lstrip('> ')),styles['CNBody']));i+=1
 return flow

def foot(c,doc):
 c.saveState();c.setStrokeColor(colors.HexColor('#cad8df'));c.line(60,43,535,43)
 c.setFont('Chinese',8);c.setFillColor(colors.HexColor('#627783'))
 c.drawString(60,29,'BRAHMS · OP.98  /  全曲深度分析');c.drawRightString(535,29,str(doc.page));c.restoreState()

def make_examples():
 src=fitz.open(SOURCE)
 # Each crop is a genuine score region. Caption names the source page rather than guessing bar bounds.
 entries=[(1,'开篇弦乐：将短小三度细胞与持续的伴随运动同时阅读。','strings'),(30,'慢乐章开篇：号角式起句与木管接力。','winds'),(42,'第三乐章开篇：高音木管的明度与齐奏能量。','winds'),(68,'终乐章主题：沿上方声部追踪八小节骨架。','winds'),(75,'终乐章中段：长笛独奏改变时间密度。','winds'),(78,'终乐章中段后续：持续音与庄严音色。','winds')]
 result=[]
 for pn,caption,kind in entries:
  p=src[pn-1];rr=rows(p,kind)
  if rr:
   cy=rr[0][0]
   top=max(20,cy-48);bottom=min(p.rect.height-20,cy+150)
  else:top=30;bottom=min(p.rect.height-20,360)
  clip=fitz.Rect(28,top,p.rect.width-22,bottom)
  if rr:
   cy,right=rr[0]
   mark=p.add_highlight_annot(fitz.Rect(max(75,right+7),cy-11,p.rect.width-25,cy+11))
   mark.set_colors(stroke=PALETTE['theme' if kind=='strings' else 'orchestration'])
   mark.set_opacity(.23);mark.update()
  dest=ASSETS/f'excerpt-{pn:02d}.png';p.get_pixmap(matrix=fitz.Matrix(2,2),clip=clip,annots=True).save(dest)
  result.append((dest,f'谱例 · 原PDF第{pn}页（原印第{pn+246}页）。{caption}'))
 src.close();return result

def report():
 files=[BASE/'overview.md']+[BASE/f'reports/movement{i}.md' for i in range(1,5)]
 combined='\n\n'.join(f.read_text(encoding='utf-8-sig') for f in files)
 (OUT/'Brahms_Op98_全曲深度分析.md').write_text(combined,encoding='utf8')
 flow=[]
 for i,f in enumerate(files):
  if i:flow.append(PageBreak())
  flow.extend(md_flow(f.read_text(encoding='utf-8-sig')))
 flow.extend([PageBreak(),Paragraph('谱面阅读窗口',styles['CNH1']),Paragraph('以下为原版谱面局部，供结合正文对照。完整上下文和高亮旁注见全曲注释总谱。',styles['CNBody'])])
 for path,caption in make_examples():
  img=Image(str(path));ratio=475/img.imageWidth;img.drawWidth=475;img.drawHeight=img.imageHeight*ratio
  flow.append(KeepTogether([img,Spacer(1,8),Paragraph(caption,styles['CNCaption']),Spacer(1,18)]))
 dest=OUT/'Brahms_Op98_全曲深度分析.pdf'
 SimpleDocTemplate(str(dest),pagesize=(595.28,841.89),rightMargin=60,leftMargin=60,topMargin=48,bottomMargin=58,title='勃拉姆斯第四交响曲：全曲深度分析',author='音乐分析研究版').build(flow,onFirstPage=foot,onLaterPages=foot)
 return dest

if __name__=='__main__':
 import sys
 if '--score' in sys.argv or '--all' in sys.argv:print(annotated_score())
 if '--report' in sys.argv or '--all' in sys.argv:print(report())
