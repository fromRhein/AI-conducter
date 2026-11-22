"""Read-only source analysis; write demonstrations only beside this script. Python 3.14+."""
from pathlib import Path
from compression import zstd
import os,json,re,struct,base64,hashlib,copy
OUT=Path(__file__).parent
PAT=re.compile(r'(?m)^\s*<VST .*\n(?:.*\n)*?\s*>')
def getblock(text): return PAT.search(text)
def unpack(block): return b''.join(base64.b64decode(s.strip()) for s in block.splitlines()[1:-1] if re.fullmatch(r'\s*[A-Za-z0-9+/=]+\s*',s))
def encode(block,state):
 raw=unpack(block); off=raw.index(bytes.fromhex('28b52ffd')); dec=zstd.ZstdDecompressor(); dec.decompress(raw[off:]); suffix=dec.unused_data
 oldsize=len(raw)-off-len(suffix); payload=json.dumps(state,separators=(',',':'),ensure_ascii=False).encode(); comp=zstd.compress(payload,level=3)
 assert off==220 and struct.unpack_from('<I',raw,216)[0]==oldsize
 prefix=bytearray(raw[:off]); struct.pack_into('<I',prefix,192,len(comp)+24);struct.pack_into('<I',prefix,204,len(comp)+8);struct.pack_into('<I',prefix,216,len(comp))
 new=bytes(prefix)+comp+suffix
 assert json.loads(zstd.decompress(new[220:220+len(comp)]))==state
 lines=block.splitlines(); result=lines[0]+'\n'+''.join('        '+base64.b64encode(new[i:i+96]).decode()+'\n' for i in range(0,len(new),96))+lines[-1]
 assert unpack(result)==new
 return result
RPP_DIR=Path(os.environ.get('RPP_DIR','D:/tools/proj'))  # 改为本机 RPP 所在目录
sources={n:RPP_DIR/(n+'.RPP') for n in ['Flute','vln1']}; hashes={n:hashlib.sha256(p.read_bytes()).hexdigest() for n,p in sources.items()}; texts={n:p.read_text() for n,p in sources.items()}
# Exact existing-state transplant is the conservative load method.
fmatch=getblock(texts['Flute']); vb=getblock(texts['vln1']).group()
trans=texts['Flute'][:fmatch.start()]+vb+texts['Flute'][fmatch.end():]
(OUT/'Flute_with_existing_Violins_state.RPP').write_text(trans)
assert unpack(getblock(trans).group())==unpack(vb)
# Patch Flute 1 to Flute 2 using only entries confirmed in installed factory index.
d=json.loads((OUT/'Flute.state.json').read_text()); index=json.loads((OUT/'SY-Prime-Woodwinds.index.bin').read_bytes()); valid=set(index['patches']['02 Woodwinds']['03 Flute 2']); changed=[]
def visit(obj):
 if isinstance(obj,dict):
  for key,value in list(obj.items()):
   if isinstance(value,str):
    new=value.replace('02 Flute 1','03 Flute 2').replace('01 Flute 1','01 Flute 2').replace('Flute 1','Flute 2').replace('FL1','FL2')
    if key=='patchEntry':
     assert new.rsplit('/',1)[1] in valid; changed.append(new)
    obj[key]=new
   else:visit(value)
 elif isinstance(obj,list):
  for value in obj:visit(value)
visit(d)
# Keep copied mixer acoustics and metadata explicitly marked experimental. Flute ranges overlap.
patched=encode(fmatch.group(),d); result=texts['Flute'][:fmatch.start()]+patched+texts['Flute'][fmatch.end():]
(OUT/'Flute2_from_Flute1_EXPERIMENTAL.RPP').write_text(result)
(OUT/'Flute2.patched.state.json').write_text(json.dumps(d,indent=2))
# Machine-readable catalog and compact markdown for every factory preset and patch.
catalog=[]
def flatten(x,path=''):
 for k,v in x.items():
  p=path+'/'+k if path else k
  if isinstance(v,dict):yield from flatten(v,p)
  else:yield p,v
for p in sorted(OUT.glob('SY-Prime-*.index.bin')):
 idx=json.loads(p.read_bytes())
 catalog.append({'volume':p.stem.replace('.index',''),'presets':[{'path':k,'entryIndex':v} for k,v in flatten(idx.get('instruments',{}))], 'patches':[{'path':'public/patches/'+k,'entryIndex':v} for k,v in flatten(idx.get('patches',{}))]})
(OUT/'factory_catalog.json').write_text(json.dumps(catalog,indent=2))
lines=[]
for c in catalog:
 lines+=['## '+c['volume'],'']
 lines += ['- `'+p['path']+'`' for p in c['presets'] if '01 VelXF sus - MOD/' in p['path']]
 lines+=['']
(OUT/'factory_presets.md').write_text('\n'.join(lines))
# Keep all branch selection and leaf reference evidence, avoiding guessed enum semantics.
def branch(n):
 return {k:v for k,v in n.items() if k in ['title','subTitle','switchControl','currentNodeIndex','whiteNoteSwitch','patchEntry','patchName','rangeFrom','rangeTo','parameters']}|({'nodes':[branch(x) for x in n['nodes']]} if 'nodes' in n else {})
for name in sources:
 state=json.loads((OUT/(name+'.state.json')).read_text()); (OUT/(name+'.articulations.json')).write_text(json.dumps(branch(state['data']['custom']['sampler']['rootNode']),indent=2))
assert hashes=={n:hashlib.sha256(p.read_bytes()).hexdigest() for n,p in sources.items()}
verification={'sourceSha256':hashes,'originalsUnchanged':True,'exactViolinTransplantByteMatch':True,'flute2PatchEntriesConfirmed':changed,'compressedStateRoundtrip':True,'runtimeAuditionPerformed':False,'warning':'Flute2 retains Flute1 mixer positioning and range; copied preset metadata does not itself trigger loading. Runtime load/audio still requires validation.'}
(OUT/'verification.json').write_text(json.dumps(verification,indent=2));print(json.dumps(verification,indent=2))
