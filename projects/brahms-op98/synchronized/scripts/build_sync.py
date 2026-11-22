from pathlib import Path
import json, bisect, base64, io
import pymupdf as fitz
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'deliverables/Brahms_IV_E_Synchronized'; OUT.mkdir(parents=True,exist_ok=True)
PERF=ROOT/'deliverables/Brahms_IV_E_Performance'
manifest=json.loads((PERF/'performance_manifest.json').read_text(encoding='utf-8'))
pts=manifest['tempo_points']; ticks=[x[0] for x in pts]
def time_at(bar):
 q=(bar-1)*3+max(0,min(bar-97,32))*3
 tick=(q-384+1.5)*960
 i=max(0,bisect.bisect_right(ticks,tick)-1)
 return pts[i][1]+(tick-pts[i][0])/960*60/pts[i][2]
bars=[{'bar':b,'time':time_at(b)} for b in range(113,313)]
assert len(bars)==200 and all(a['time']<b['time'] for a,b in zip(bars,bars[1:]))
assert abs(bars[-1]['time']-manifest['duration_before_reverb_seconds'])<1e-8
page_map=json.loads((ROOT/'sync_work/page_map.json').read_text(encoding='utf-8'))
if isinstance(page_map,dict): page_map=page_map.get('pages',page_map.get('page_map'))
assert [p['page'] for p in page_map]==list(range(76,99))
assert all(p['start']<page_map[i+1]['start'] for i,p in enumerate(page_map[:-1]))
doc=fitz.open(ROOT/'deliverables/Brahms_Op98_全曲注释总谱.pdf')
images=[]
for p in page_map:
 page=doc[p['page']]
 raw=(ROOT/'sync_work/page_images'/f"{p['page']}.webp").read_bytes()
 images.append('data:image/webp;base64,'+base64.b64encode(raw).decode())
 p['time']=time_at(max(113,p['start']))
 p['width']=page.rect.width; p['height']=page.rect.height
 for s in p.get('systems',[]): s['time']=time_at(max(113,s['start']))
notes=[n for n in json.loads((ROOT/'annotations.json').read_text(encoding='utf-8')) if n['movement']==4 and n['end']>=113]
audio='data:audio/mpeg;base64,'+base64.b64encode((PERF/'Brahms_IV_E_to_End_VSL.mp3').read_bytes()).decode()
data={'pages':page_map,'bars':bars,'notes':notes,'images':images,'audio':audio,'duration':329.0614375,'musicEnd':manifest['duration_before_reverb_seconds']}
component=(ROOT/'sync_work/player_component.txt').read_text(encoding='utf-8').replace('__SYNC_DATA__',json.dumps(data,ensure_ascii=False,separators=(',',':')))
draft='''---
title: 勃拉姆斯第四交响曲 · 分析总谱同步聆听
subtitle: 第四乐章 E（第113小节）至终曲 · VSL 指挥演绎 · 5分29秒
template: doc
theme: paper
mode: light
style: off
---
## A 播放与跟谱
```html
'''+component+'''
```
## B 阅读方式
点击播放，谱页随录音自动切换。上方显示当前小节，并同步展示相应分析。可按小节跳转、选择谱页、改变播放速度和放大总谱；手动选页会暂停自动翻页，点击“恢复跟谱”回到当前音乐位置。

录音和23张带标注总谱均内嵌在本页，保存此单个文件即可离线使用。请用桌面浏览器打开；若文档预览禁止脚本或音频，请下载后用 Edge 或 Chrome 打开。

同步时间来自这次演奏的实际速度图，包含起音前留白、渐变速度、第128小节停顿和末尾混响。当前小节表示谱面拍点；采样起音和人性化偏移会带来毫秒级差异。高亮沿用原分析总谱，当前系统边框辅助跟读，未绘制逐音符游标。原注释中保留的“跨页参考段”属于分析覆盖范围，不是播放器当前小节。
'''
(OUT/'同步播放器_源稿.md').write_text(draft,encoding='utf-8')
(OUT/'同步时间表.json').write_text(json.dumps({k:v for k,v in data.items() if k not in ['images','audio']},ensure_ascii=False,indent=2),encoding='utf-8')
print('draft',len(draft),'pages',len(images),'bars',len(bars),'first',bars[0],'last',bars[-1])
