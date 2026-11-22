import socket,struct,json,os,base64,subprocess,time,urllib.request,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'deliverables/Brahms_IV_E_Synchronized'
class CDP:
 def __init__(self,url):
  from urllib.parse import urlparse
  u=urlparse(url); self.s=socket.create_connection((u.hostname,u.port),30); self.n=0; self.events=[]
  key=base64.b64encode(os.urandom(16)).decode()
  self.s.sendall(f'GET {u.path} HTTP/1.1\r\nHost: {u.netloc}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\nOrigin: http://localhost\r\n\r\n'.encode())
  h=b''
  while b'\r\n\r\n' not in h:h+=self.s.recv(1)
  assert b'101' in h,h
 def read(self,n):
  b=b''
  while len(b)<n:
   c=self.s.recv(n-len(b))
   if not c:raise EOFError()
   b+=c
  return b
 def send(self,d):
  b=json.dumps(d).encode(); n=len(b);mask=os.urandom(4)
  h=bytes([129,128|n]) if n<126 else bytes([129,254])+struct.pack('!H',n) if n<65536 else bytes([129,255])+struct.pack('!Q',n)
  self.s.sendall(h+mask+bytes(x^mask[i%4] for i,x in enumerate(b)))
 def receive(self):
  payload=b''
  while True:
   a,b=self.read(2);n=b&127
   if n==126:n=struct.unpack('!H',self.read(2))[0]
   if n==127:n=struct.unpack('!Q',self.read(8))[0]
   mask=self.read(4) if b&128 else None; chunk=self.read(n)
   if mask:chunk=bytes(x^mask[i%4] for i,x in enumerate(chunk))
   if a&15==8:raise EOFError()
   payload+=chunk
   if a&128:return json.loads(payload)
 def call(self,method,params=None):
  self.n+=1;self.send({'id':self.n,'method':method,'params':params or {}})
  while True:
   r=self.receive()
   if r.get('method')=='Runtime.exceptionThrown':self.events.append(r)
   if r.get('id')==self.n:
    if 'error' in r:raise RuntimeError(r)
    return r.get('result',{})
 def js(self,expression):
  r=self.call('Runtime.evaluate',{'expression':expression,'returnByValue':True,'awaitPromise':True})
  if 'exceptionDetails' in r:raise RuntimeError(r)
  return r['result'].get('value')
with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
proc=subprocess.Popen(['C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe','--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check','--remote-allow-origins=*','--autoplay-policy=no-user-gesture-required',f'--remote-debugging-port={port}',f'--user-data-dir={ROOT / "sync_work/edge_test_profile"}','about:blank'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
client=None
try:
 opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
 for _ in range(100):
  try:
   tabs=json.loads(opener.open(f'http://127.0.0.1:{port}/json',timeout=1).read());break
  except Exception:time.sleep(.2)
 client=CDP(next(x['webSocketDebuggerUrl'] for x in tabs if x['type']=='page'))
 client.call('Page.enable');client.call('Runtime.enable');client.call('Network.enable');client.call('Network.emulateNetworkConditions',{'offline':True,'latency':0,'downloadThroughput':-1,'uploadThroughput':-1});client.call('Emulation.setDeviceMetricsOverride',{'width':1440,'height':1100,'deviceScaleFactor':1,'mobile':False})
 client.call('Page.navigate',{'url':(OUT/'Brahms_IV_E_分析总谱同步播放器.html').as_uri()})
 for _ in range(150):
  if client.js('Boolean(window.scoreSyncTest && document.getElementById("syncAudio").readyState>=1)'):break
  time.sleep(.2)
 assert client.js('Boolean(window.scoreSyncTest)'), json.dumps({'events':client.events,'dom':client.js('({url:location.href,ready:document.readyState,title:document.title,audio:!!document.getElementById("syncAudio"),status:document.getElementById("syncStatus")?.textContent})')},ensure_ascii=False)
 result=client.js('''(async()=>{const T=scoreSyncTest,a=document.getElementById('syncAudio'),d=T.data;const errors=[];for(const b of d.bars.filter(x=>x.bar<=311)){T.seek(b.time+.02);let expected=0;d.pages.forEach((p,i)=>{if(p.time<=b.time+.02)expected=i});if(T.getPage()!==expected)errors.push({bar:b.bar,expected,actual:T.getPage()});if(!document.getElementById('syncStatus').textContent.includes(String(b.bar)))errors.push({bar:b.bar,status:document.getElementById('syncStatus').textContent});}T.seek(0);await a.play();await new Promise(r=>setTimeout(r,350));a.pause();const advanced=a.currentTime>0;document.getElementById('barInput').value=253;document.getElementById('seekBar').click();const jump=Math.abs(a.currentTime-d.bars[140].time)<.001;document.getElementById('previousPage').click();const manual=!T.getFollowing();document.getElementById('followToggle').click();const follow=T.getFollowing();const pictures=await Promise.all(d.images.map(src=>new Promise(resolve=>{let i=new Image;i.onload=()=>resolve({width:i.width,height:i.height});i.onerror=()=>resolve(null);i.src=src})));T.seek(0);return {errors,advanced,jump,manual,follow,pictures,duration:a.duration,readyState:a.readyState,pageCount:d.pages.length,barCount:d.bars.length-1,audioError:a.error?.message||null}})()''')
 assert not result['errors'],result['errors']
 assert all(result[k] for k in ['advanced','jump','manual','follow'])
 assert all(result['pictures']) and len(result['pictures'])==23
 assert abs(result['duration']-329.0614375)<.1
 screenshot=client.call('Page.captureScreenshot',{'format':'png','captureBeyondViewport':False})
 (OUT/'播放器预览.png').write_bytes(base64.b64decode(screenshot['data']))
 result['html_sha256']=hashlib.sha256((OUT/'Brahms_IV_E_分析总谱同步播放器.html').read_bytes()).hexdigest()
 (OUT/'播放器验证.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({k:v for k,v in result.items() if k!='pictures'},ensure_ascii=False))
finally:
 if client:
  try:client.call('Browser.close')
  except Exception:pass
 try:proc.wait(timeout=10)
 except subprocess.TimeoutExpired:proc.terminate()
