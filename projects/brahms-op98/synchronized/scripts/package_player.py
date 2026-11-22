from pathlib import Path
import zipfile,json,hashlib
root=Path(__file__).resolve().parents[1];d=root/'deliverables/Brahms_IV_E_Synchronized'
names=['Brahms_IV_E_分析总谱同步播放器.html','使用说明.md','同步时间表.json','播放器验证.json']
report=json.loads((d/'播放器验证.json').read_text(encoding='utf-8'))
assert report['errors']==[] and report['pageCount']==23 and report['barCount']==199
assert report['html_sha256']==hashlib.sha256((d/names[0]).read_bytes()).hexdigest()
z=d/'Brahms_IV_E_分析总谱同步播放_离线包.zip'
with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
 for name in names:archive.write(d/name,name)
with zipfile.ZipFile(z) as archive:assert archive.testzip() is None
print('ZIP:',z,'bytes:',z.stat().st_size)
print('Verified final HTML hash:',report['html_sha256'])
