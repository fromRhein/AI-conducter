from pathlib import Path
import urllib.request,xml.etree.ElementTree as ET,json
out=Path(__file__).resolve().parent/'digital';out.mkdir(exist_ok=True)
u='https://openscorearchive.project-pioneer.com/media/musicxml/1657/raw'
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
data=opener.open(u,timeout=60).read();root=ET.fromstring(data)
(out/'Buelow_reference.musicxml').write_bytes(data)
parts=[]
for p in root.findall('part'):
 ms=p.findall('measure');summary=[]
 for m in ms:
  marks=[e.text for e in m.findall('.//words') if e.text]
  keys=[e.text for e in m.findall('.//fifths')];times=[(e.findtext('beats'),e.findtext('beat-type')) for e in m.findall('.//time')]
  if marks or keys or times:summary.append({'measure':m.get('number'),'words':marks,'keys':keys,'time':times})
 parts.append({'part':p.get('id'),'measures':len(ms),'marks':summary})
(out/'reference_index.json').write_text(json.dumps(parts,ensure_ascii=False,indent=2),encoding='utf-8')
print('bytes',len(data),'parts',[(x['part'],x['measures']) for x in parts]);print(json.dumps(parts,ensure_ascii=False)[:13000])
