from pathlib import Path
import json
import numpy as np
import pymupdf as fitz
ROOT=Path(__file__).resolve().parent

def detect(page):
 scale=2
 pm=page.get_pixmap(matrix=fitz.Matrix(scale,scale),colorspace=fitz.csGRAY)
 a=np.frombuffer(pm.samples,np.uint8).reshape(pm.height,pm.width)
 lo,hi=int(pm.width*.28),int(pm.width*.94)
 v=(a[:,lo:hi]<150).mean(1)
 ids=np.flatnonzero(v>.42)
 groups=np.split(ids,np.flatnonzero(np.diff(ids)>1)+1)
 ys=[float(g.mean()/scale) for g in groups if len(g)]
 staves=[];i=0
 while i+4<len(ys):
  ss=ys[i:i+5];ds=np.diff(ss)
  if 2.0<np.median(ds)<6 and max(ds)-min(ds)<1.1:
   staves.append(ss);i+=5
  else:i+=1
 return a,staves

def marks(page):
 a,staves=detect(page);out=[]
 if len(staves)<8:return out
 selections=[(ss,'orchestration') for ss in staves[:2]]+[(ss,'theme') for ss in staves[-2:]]
 for ss,kind in selections:
  cy=float(np.mean(ss))
  # Estimate tilt from the five actual staff lines at multiple horizontal windows.
  xs=np.linspace(page.rect.width*.3,page.rect.width*.91,8);points=[]
  for x in xs:
   col=(a[:,int(x*2-18):int(x*2+18)]<150).mean(1)
   yy=[]
   for base in ss:
    l=max(0,int((base-1.6)*2));r=min(len(col),int((base+1.6)*2)+1)
    j=l+int(np.argmax(col[l:r]));yy.append(j/2)
   points.append(float(np.mean(yy)))
  slope,intercept=np.polyfit(xs,points,1)
  error=float(max(abs(np.array(points)-(slope*xs+intercept))))
  if error>1.2:continue
  x0=page.rect.width*.28;x1=page.rect.width*.94
  half=(ss[-1]-ss[0])/2+2.0
  y0=slope*x0+intercept;y1=slope*x1+intercept
  quad=[(x0+14,y0-half+48),(x1+14,y1-half+48),(x0+14,y0+half+48),(x1+14,y1+half+48)]
  out.append({'kind':kind,'quad':quad,'staff_lines':ss,'fit_error_pt':error,'old_label_center':cy,'staff_center':float(np.mean(ss))})
 return out

def main():
 out=ROOT.parent/'deliverables/Wagner_Meistersinger_Original'
 old=out/'Wagner_名歌手前奏曲_原作注释总谱.pdf'
 doc=fitz.open(old);src=fitz.open(ROOT/'Schott_18469_original.pdf');audit=[]
 for i,p in enumerate(src):
  target=doc[i+1]
  for ann in list(target.annots() or []):target.delete_annot(ann)
  entries=marks(p)
  for e in entries:
   ann=target.add_highlight_annot(fitz.Quad(e['quad']));ann.set_colors(stroke=(.98,.85,.22) if e['kind']=='theme' else (.3,.82,.91));ann.set_opacity(.18)
   ann.set_info(title='五线谱定位的声部观察带',content='根据五条谱线像素位置与局部倾斜拟合定位；不是逐音主题标签。');ann.update()
  audit.append({'page':i+1,'marks':entries})
 corrected=out/'Wagner_名歌手前奏曲_原作注释总谱_高亮校正版.pdf'
 doc.save(corrected,garbage=4,deflate=True);doc.close()
 (out/'highlight_alignment_check.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf8')
 print('pages',len(audit),'marks',sum(len(x['marks']) for x in audit),'pages_without_mark',[x['page'] for x in audit if not x['marks']])
 print('max_line_fit_error',max(e['fit_error_pt'] for x in audit for e in x['marks']))
 print(corrected)
if __name__=='__main__':main()
