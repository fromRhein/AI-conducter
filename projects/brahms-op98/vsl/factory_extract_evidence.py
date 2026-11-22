"""Bounded read-only inspection; never reads/decrypts license payload or samples."""
from pathlib import Path
from compression import zstd
import struct,json,math,collections,hashlib,zlib,bz2,lzma
OUT=Path(__file__).parent
paths=[Path('C:/ProgramData/VSL/Vienna Synchron Player/Volumes/at.co.vsl.synchronplayer.syvolume'),*Path('D:/VSL Libraries').glob('*/*.syvolume')]
def entropy(b):
 c=collections.Counter(b);n=len(b);return round(-sum(v/n*math.log2(v/n) for v in c.values()),6)
def flatten(x,path=''):
 for k,v in x.items():
  p=path+'/'+k if path else k
  if isinstance(v,dict):yield from flatten(v,p)
  else:yield p,v
report=[]
for p in paths:
 with p.open('rb') as f:
  h=f.read(40);a=struct.unpack('<10I',h);idxoff=a[5];tableoff=a[6];dataoff=a[7]
  f.seek(40);meta=json.loads(f.read(a[9]))
  f.seek(idxoff);n=struct.unpack('<I',f.read(4))[0];index=json.loads(zstd.decompress(f.read(n)))
  presets=[{'path':k,'entryIndex':v} for k,v in flatten(index.get('instruments',{})) if k.endswith('.vsynpreset')]
  selected=[x for x in presets if '/01 VelXF sus - MOD/' in x['path']]
  if 'Harp' in p.stem or 'Percussion' in p.stem:selected=[x for x in presets if 'SYNCHRON Prime Orchestra/' in x['path']]
  f.seek(tableoff);tn=struct.unpack('<I',f.read(4))[0];b=f.read(tn)
  trials={}
  for name,decode in [('zstd',zstd.decompress),('zlib',zlib.decompress),('gzip',lambda x:zlib.decompress(x,31)),('bz2',bz2.decompress),('xz',lzma.decompress)]:
   try:trials[name]={'decodedBytes':len(decode(b))}
   except Exception as e:trials[name]=str(e)
  f.seek(dataoff);first=f.read(68)
  r={'volume':str(p),'fileSize':p.stat().st_size,'magic':h[:4].decode(),'versionBytes':h[4:8].hex(),'metadataKeys':list(meta),'contentVersion':meta.get('contentVersion'),'metadataEnd':40+a[9],'opaquePreIndexStart':a[3],'unknownRegionEnd':a[4],'indexOffset':idxoff,'indexCompressedBytes':n,'tableCandidateOffset':tableoff,'tableCandidateLength':tn,'tableCandidateEnd':tableoff+4+tn,'paddingBeforeData':dataoff-tableoff-4-tn,'dataStart':dataoff,'dataAligned4096':dataoff%4096==0,'tableEntropyBitsPerByte':entropy(b),'tableSha256':hashlib.sha256(b).hexdigest(),'tablePrefixHex':b[:32].hex(),'tableZstdMagicCount':b.count(bytes.fromhex('28b52ffd')),'tableJSONMarkerCount':b.count(b'"rootNode"'),'tableDecoders':trials,'firstDataLength':struct.unpack_from('<I',first)[0],'firstDataPrefixHex':first[4:36].hex(),'indexedEntries':len(list(flatten(index))),'presetCount':len(presets),'selectedPresetCount':len(selected),'selectedPresets':selected,'allPresetCatalog':presets}
  r['tableLengthMinus4Div24']=(tn-4)//24 if (tn-4)%24==0 else None
  r['tableFirstLE32']=struct.unpack_from('<I',b)[0]
  report.append(r)
  print(p.name,'table',tn,'entropy',r['tableEntropyBitsPerByte'],'presets',len(presets),'selected',len(selected),'padding',r['paddingBeforeData'])
(OUT/'archive_evidence.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
