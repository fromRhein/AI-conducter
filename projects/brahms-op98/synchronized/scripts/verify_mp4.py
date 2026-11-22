from pathlib import Path
import subprocess,json,bisect,math
import numpy as np
from PIL import Image
R=Path(__file__).resolve().parents[1];O=R/'deliverables/Brahms_IV_E_Synchronized';W=R/'sync_work/mp4_frames';V=O/'Brahms_IV_E_分析总谱同步_4K.mp4'
FF='C:/Users/rhein/AppData/Local/ffmpeg/current/bin/ffmpeg.exe';FP='C:/Users/rhein/AppData/Local/ffmpeg/current/bin/ffprobe.exe'
meta=json.loads(subprocess.check_output([FP,'-v','error','-show_format','-show_streams','-of','json',str(V)]))
v=next(s for s in meta['streams'] if s['codec_type']=='video');a=next(s for s in meta['streams'] if s['codec_type']=='audio')
assert (v['width'],v['height'])==(3840,2160) and v['codec_name']=='h264'
assert a['codec_name']=='aac' and int(a['sample_rate'])==48000 and a['channels']==2
assert abs(float(meta['format']['duration'])-329.0614375)<.07
states=json.loads((O/'MP4同步核验表.json').read_text(encoding='utf-8'))
frame_meta=json.loads(subprocess.check_output([FP,'-v','error','-select_streams','v:0','-show_entries','frame=best_effort_timestamp_time','-of','json',str(V)]))['frames']
assert len(frame_meta) in [len(states),len(states)+1],len(frame_meta)
time_errors=[abs(float(frame_meta[i]['best_effort_timestamp_time'])-s['time']) for i,s in enumerate(states)]
assert max(time_errors)<=1/30+.002,max(time_errors)
frames=W/'verified_frames';frames.mkdir(exist_ok=True)
cmd=[FF,'-hide_banner','-v','error','-threads','4','-i',str(V),'-vf','scale=960:540','-fps_mode','vfr',str(frames/'%03d.png')]
subprocess.run(cmd,check=True)
actual=sorted(frames.glob('*.png'));assert len(actual)==len(frame_meta),(len(actual),len(frame_meta))
errors=[]
for p,s in zip(actual,states):
 im=np.asarray(Image.open(p).convert('RGB'),dtype=np.float32)
 ref=np.asarray(Image.open(W/s['frame_file']).convert('RGB').resize((960,540),Image.Resampling.BICUBIC),dtype=np.float32)
 mae=float(np.mean(np.abs(im-ref)));errors.append(mae)
 assert mae<6,(s['bar'],mae)
def pcm(path,t):
 return np.frombuffer(subprocess.check_output([FF,'-v','error','-ss',str(t),'-i',str(path),'-t','2','-vn','-ac','1','-ar','8000','-f','f32le','pipe:1']),dtype=np.float32)
corr=[]
for t in [10,100,250,320]:
 x=pcm(V,t);y=pcm(R/'deliverables/Brahms_IV_E_Performance/Brahms_IV_E_to_End_VSL_48k24.wav',t);n=min(len(x),len(y));c=float(np.corrcoef(x[:n],y[:n])[0,1]);corr.append({'seconds':t,'correlation':c});assert c>.98,(t,c)
report={'resolution':[v['width'],v['height']],'frame_rate':v['r_frame_rate'],'variable_frame_rate':True,'maximum_transition_error_seconds':max(time_errors),'video_codec':v['codec_name'],'audio_codec':a['codec_name'],'audio_sample_rate':a['sample_rate'],'duration':meta['format']['duration'],'bytes':V.stat().st_size,'verified_visual_states':len(states),'maximum_scaled_pixel_MAE':max(errors),'audio_waveform_correlations':corr,'method':'Full video decoded; each measure/pre-roll/tail frame compared with its planned image. Audio compared with final WAV at four timestamps.'}
(O/'MP4验证结果.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
