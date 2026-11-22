from pathlib import Path
import json
OUT=Path(__file__).parent
result={}
for name in ['Flute','vln1']:
 d=json.loads((OUT.parent/'vsl_probe'/f'{name}.state.json').read_text())
 c=d['data']['custom']
 def tree(n):
  keys=['title','subTitle','switchControl','whiteNoteSwitch','currentNodeIndex','rangeFrom','rangeTo','patchEntry','patchName']
  out={k:n[k] for k in keys if k in n}
  if 'nodes' in n:out['nodes']=[tree(x) for x in n['nodes']]
  return out
 result[name]={'provenance':'Existing RPP state, NOT newly extracted factory preset','lastPresetPath':c['lastPresetPath'],'mappings':c['paramControl'],'tree':tree(c['sampler']['rootNode'])}
 print(name,'PATH',c['lastPresetPath'])
 root=c['sampler']['rootNode']
 for n in root['nodes']:print({k:n[k] for k in ['title','rangeFrom','rangeTo','switchControl','whiteNoteSwitch'] if k in n})
(OUT/'existing_state_mappings.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
