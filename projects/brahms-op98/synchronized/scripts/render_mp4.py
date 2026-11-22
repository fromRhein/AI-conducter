from pathlib import Path
import json,bisect,subprocess
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).resolve().parents[1];W=R/'sync_work/mp4_frames';W.mkdir(parents=True,exist_ok=True)
O=R/'deliverables/Brahms_IV_E_Synchronized';D=json.loads((O/'同步时间表.json').read_text(encoding='utf-8'))
FF='C:/Users/rhein/AppData/Local/ffmpeg/current/bin/ffmpeg.exe'
FONT='C:/Windows/Fonts/simhei.ttf'
def f(n):return ImageFont.truetype(FONT,n)
fonts={n:f(n) for n in [30,36,42,48,52,64,96]}
def wrap(text,font,width):
 lines=[];line=''
 for c in text:
  if c=='\n' or font.getlength(line+c)>width:
   lines.append(line);line='' if c=='\n' else c
  else:line+=c
 if line:lines.append(line)
 return lines
page_times=[p['time'] for p in D['pages']]
cache={}
for i,p in enumerate(D['pages']):
 im=Image.open(R/f"sync_work/page_images/{p['page']}.webp").convert('RGB')
 h=1960;w=round(im.width*h/im.height);im=im.resize((w,h),Image.Resampling.LANCZOS)
 cache[i]=im
states=[{'time':0,'bar':113,'label':'准备起奏'}]+[{'time':b['time'],'bar':b['bar'],'label':None} for b in D['bars'] if b['bar']<=311]+[{'time':D['musicEnd'],'bar':311,'label':'终止和弦 · 余响'}]
concat=['ffconcat version 1.0'];audit=[]
for i,state in enumerate(states):
 t=state['time'];bar=state['bar'];pi=max(0,bisect.bisect_right(page_times,t)-1);p=D['pages'][pi]
 image=Image.new('RGB',(3840,2160),'#101d29');draw=ImageDraw.Draw(image)
 draw.text((42,28),'BRAHMS  /  SYMPHONY No.4  /  Op.98',font=fonts[36],fill='#c3d3df')
 score=cache[pi];x=42;y=112;image.paste(score,(x,y))
 ss=p['systems'];s=ss[max(0,bisect.bisect_right([a['start'] for a in ss],bar)-1)];si=ss.index(s)
 y0=s['y']+48;y1=ss[si+1]['y']+42 if si+1<len(ss) else p['height']-28
 scale=1960/p['height'];draw.rectangle((x+14*scale,y+y0*scale,x+(p['width']-296)*scale,y+y1*scale),outline='#0099bc',width=6)
 tx=x+score.width+70;tw=3840-tx-65
 draw.text((tx,132),'第四乐章 · E 至终曲',font=fonts[64],fill='white')
 draw.text((tx,238),state['label'] or f'第 {bar} 小节',font=fonts[96],fill='#6fddd2')
 draw.text((tx,370),f'原谱第 {p["page"]+246} 页  |  第113–311小节',font=fonts[42],fill='#bdccd7')
 n=next((n for n in D['notes'] if n['start']<=bar<=n['end']),None)
 yy=490
 if n:
  for line in wrap(f'{n["title"]}  ·  {n["start"]}–{n["end"]}',fonts[52],tw):
   draw.text((tx,yy),line,font=fonts[52],fill='#f6d899');yy+=76
  yy+=40
  for line in wrap(n['text'],fonts[48],tw):
   draw.text((tx,yy),line,font=fonts[48],fill='#e1e9ee');yy+=76
 assert yy<1860,(bar,yy)
 draw.text((tx,1900),'青色框：当前系统',font=fonts[36],fill='#75d9e8')
 draw.text((tx,1960),'VSL 管弦乐演绎 · 原分析荧光标注保留',font=fonts[30],fill='#a8b9c7')
 draw.text((42,2100),'分析总谱同步聆听  |  5:29',font=fonts[30],fill='#a8b9c7')
 draw.rectangle((42,2084,3798,2089),fill='#354553');draw.rectangle((42,2084,42+3756*t/D['duration'],2089),fill='#60cbbb')
 filename=W/f'{i:03}.png'
 if not filename.exists():image.save(filename,compress_level=2)
 duration=(states[i+1]['time'] if i+1<len(states) else D['duration'])-t
 concat += [f"file '{filename.as_posix()}'",'option framerate 30',f'duration {duration:.9f}']
 audit.append({'time':t,'duration':duration,'bar':bar,'source_page':p['page'],'frame_file':filename.name})
concat += [f"file '{filename.as_posix()}'",'option framerate 30']
(W/'timeline.ffconcat').write_text('\n'.join(concat)+'\n',encoding='utf-8')
(O/'MP4同步核验表.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
output=O/'Brahms_IV_E_分析总谱同步_4K.mp4'
cmd=[FF,'-hide_banner','-y','-f','concat','-safe','0','-i',str(W/'timeline.ffconcat'),'-i',str(R/'deliverables/Brahms_IV_E_Performance/Brahms_IV_E_to_End_VSL_48k24.wav'),'-map','0:v:0','-map','1:a:0','-fps_mode','vfr','-c:v','libx264','-preset','veryfast','-tune','stillimage','-crf','18','-pix_fmt','yuv420p','-threads','4','-c:a','aac','-b:a','320k','-ar','48000','-t',str(D['duration']+1/30),'-movflags','+faststart','-metadata','title=Brahms IV E to End - Annotated Score','-progress',str(W/'encode_progress.txt'),str(output)]
print('Frames ready:',len(states),'encoding:',output,flush=True)
with (W/'encode.log').open('w',encoding='utf-8') as log:
 subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True)
print('Complete:',output.stat().st_size,flush=True)
