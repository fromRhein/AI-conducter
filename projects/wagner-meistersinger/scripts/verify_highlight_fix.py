from pathlib import Path
import json,shutil
import numpy as np
import pymupdf as f
base=Path(__file__).resolve().parent.parent
out=base/'deliverables/Wagner_Meistersinger_Original'
source=f.open(base/'wagner_work/Schott_18469_original.pdf')
fixed=out/'Wagner_名歌手前奏曲_原作注释总谱_高亮校正版.pdf'
doc=f.open(fixed)
audit=json.loads((out/'highlight_alignment_check.json').read_text(encoding='utf8'))
assert len(doc)==40 and len(audit)==39
worst=0;count=0
for i,p in enumerate(source):
 target=doc[i+1];anns=list(target.annots() or [])
 assert len(anns)==len(audit[i]['marks'])==4
 for ann,entry in zip(anns,audit[i]['marks']):
  assert np.max(np.abs(np.array(ann.vertices)-np.array(entry['quad'])))<.001
  q=entry['quad'];lines=entry['staff_lines']
  assert q[0][1]-48 < lines[0]+2 and q[2][1]-48 > lines[-1]-2
  count+=1
 a=p.get_pixmap(matrix=f.Matrix(.5,.5),colorspace=f.csGRAY)
 z=target.get_pixmap(matrix=f.Matrix(.5,.5),colorspace=f.csGRAY,clip=f.Rect(14,48,p.rect.width+14,p.rect.height+48),annots=False)
 assert (a.width,a.height)==(z.width,z.height)
 worst=max(worst,float(np.abs(np.frombuffer(a.samples,np.uint8).astype(int)-np.frombuffer(z.samples,np.uint8).astype(int)).mean()))
doc.close();source.close()
result={'pages_checked':39,'annotations_checked':count,'quad_roundtrip_tolerance_pt':.001,'max_staff_line_fit_residual_pt':max(e['fit_error_pt'] for p in audit for e in p['marks']),'source_image_mean_abs_difference_max':worst,'visual_review':False,'method':'Five-line raster groups, local slope fitting; removed OCR-positioned annotations'}
(out/'highlight_correction_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
original=out/'Wagner_名歌手前奏曲_原作注释总谱.pdf'
backup=base/'wagner_work/Wagner_before_highlight_correction.pdf'
if not backup.exists():shutil.copy2(original,backup)
shutil.copy2(fixed,original)
print(json.dumps(result,ensure_ascii=False))
