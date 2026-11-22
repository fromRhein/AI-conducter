from pathlib import Path
import sys,json
import pymupdf as fitz
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
import build_deliverables as b
from fix_highlight_alignment import detect
ROOT=Path(__file__).resolve().parent; BASE=ROOT.parent
OUT=BASE/'deliverables/Wagner_Meistersinger_Original'; SRC=ROOT/'Schott_18469_original.pdf'; FONT=b.FONT
COL={'A':(.98,.72,.12),'B':(.98,.72,.12),'A′':(.98,.58,.10),'L':(.35,.75,.96),'P':(.35,.75,.96),'IM':(.70,.45,.95),'CP':(.95,.40,.55),'H':(.35,.80,.52),'O':(.45,.65,.90),'A/B':(.98,.68,.16),'A→L':(.45,.75,.96),'L/P':(.35,.75,.96),'A′→A':(.98,.58,.10),'A/B/L/P':(.95,.50,.20),'H/O':(.40,.78,.50)}

def main():
 notes=json.loads((ROOT/'detailed_annotations.json').read_text(encoding='utf8')); src=fitz.open(SRC);d=fitz.open();p=d.new_page(width=1000,height=900);p.insert_font(fontname='CN',fontfile=FONT)
 y=b.text_at(p,50,80,'瓦格纳《名歌手》前奏曲 · 原作动机与写作技法标注版',900,24)
 for t in ['本版专门标注：A/B公共性材料、L/P抒情材料、A′碎片化、IM模仿／fugato、CP复合对位、H和声功能、O配器承载。','每一条色带对应一个“谱组阅读窗口”，旁边标签说明应追踪的材料关系；它不是把整行声部笼统涂色。','由于历史PDF没有可直接解析的音符层，谱组定位已按五条谱线像素检测；动机名称与写作技术来自逐页阅读框架及文献证据，精确音符归属仍需人工放大核谱。']:y=b.text_at(p,50,y+25,t,890,13)
 for i,sp in enumerate(src):
  w,h=sp.rect.width,sp.rect.height;p=d.new_page(width=w+310,height=h+72);p.insert_font(fontname='CN',fontfile=FONT);p.show_pdf_page(fitz.Rect(14,48,w+14,h+48),src,i)
  x=w+32;ww=252;p.draw_rect(fitz.Rect(x-9,48,w+300,h+48),fill=(.96,.97,.98),color=None)
  pageinfo=notes[i];y=b.text_at(p,x,74,f'Schott 第{i+1}页 · {pageinfo["phase"]}',ww,12)
  staves=detect(sp)[1]; picks=np.linspace(0,len(staves)-1,4).round().astype(int) if staves else []
  for j,item in enumerate(pageinfo['items']):
   y+=16; col=COL.get(item['label'],(.8,.5,.3));p.draw_rect(fitz.Rect(x,y-10,x+5,y+5),fill=col,color=None);y=b.text_at(p,x+13,y,item['label']+'  '+item['text'],ww-13,9.3)
   if j<len(picks):
    ss=staves[picks[j]]; y0=float(ss[0])-3;y1=float(ss[-1])+3; q=fitz.Quad([(w*.28+14,y0+48),(w*.94+14,y0+48),(w*.28+14,y1+48),(w*.94+14,y1+48)])
    a=p.add_highlight_annot(q);a.set_colors(stroke=col);a.set_opacity(.20);a.set_info(title=item['label']+' 写作技法定位',content=item['text']+'；定位为谱组窗口，不等于逐音主题边界。');a.update()
    p.insert_text((20,y0+53),item['label'],fontname='CN',fontsize=7,color=col)
  p.insert_text((20,h+63),f'Schott 18469 | source {i+1}/39 | motif/technique study edition',fontsize=8)
 d.set_toc([[1,'说明',1]]+[[1,f'第{i}页 · '+notes[i-1]['phase'],i+1] for i in [1,4,8,12,16,20,24,28,32,36,39]])
 d.subset_fonts();path=OUT/'Wagner_名歌手前奏曲_动机与写作技法标注总谱.pdf';d.save(path,garbage=4,deflate=True);print(path)
if __name__=='__main__':main()
