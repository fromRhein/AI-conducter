"""After rerendering the two main and four auxiliary VSL projects, rebuild their aligned stems.
Requires Python and numpy. Run from any directory; paths stay relative to this file.
"""
from pathlib import Path
import json,wave,numpy as np
O=Path(__file__).resolve().parent
manifest=json.loads((O/'render_manifest.json').read_text())
for parent in ['11_Horn2_staff6','16_TenorTrombone_staff9']:
 files=[O/'aux_audio'/(parent+'_main.wav')]+[O/'aux_audio'/Path(a['wav']).name for a in manifest['auxiliary_instances'] if a['parent']==parent]
 mix=None;shape=None
 for path in files:
  with wave.open(str(path),'rb') as f:
   fmt=(f.getframerate(),f.getnchannels(),f.getsampwidth(),f.getnframes());raw=f.readframes(f.getnframes())
  assert fmt[1:3]==(2,3),'Expected stereo 24-bit PCM'
  assert shape is None or shape==fmt,'Components must have identical format and length'
  shape=fmt;b=np.frombuffer(raw,np.uint8).reshape(-1,3);x=b[:,0].astype(np.int32)|(b[:,1].astype(np.int32)<<8)|(b[:,2].astype(np.int32)<<16);x=np.where(x>=8388608,x-16777216,x).astype(np.int64);mix=x if mix is None else mix+x
 assert np.max(np.abs(mix))<8388608,'Sum clips; reduce source gains before recombining'
 b=np.empty((len(mix),3),np.uint8);b[:,0]=mix&255;b[:,1]=(mix>>8)&255;b[:,2]=(mix>>16)&255
 target=O/'stems'/(parent+'.wav');temp=target.with_suffix('.rebuild.wav')
 with wave.open(str(temp),'wb') as f:f.setnchannels(2);f.setsampwidth(3);f.setframerate(shape[0]);f.writeframes(b.tobytes())
 temp.replace(target);print('Updated',target.name)
