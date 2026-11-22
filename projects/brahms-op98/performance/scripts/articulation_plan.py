"""Import-safe XML/MIDI articulation mapping. CLI writes only articulation_plan.json."""
from pathlib import Path
from fractions import Fraction
from collections import defaultdict, Counter
import xml.etree.ElementTree as ET
import json
import mido
START, END, PRE, TPQ = 384., 1029., 1.5, 960
DUR = {'long':16,'breve':8,'whole':4,'half':2,'quarter':1,'eighth':.5,'16th':.25,'32nd':.125,'64th':.0625,'128th':.03125}
PRESETS = [['Flute1','Flute2'],['Oboe1','Oboe2'],['Clarinet1','Clarinet2'],['Bassoon1','Bassoon2'],['Contrabassoon'],['Horn1','Horn2'],['Horn1','Horn2'],['Trumpet1','Trumpet2'],['TenorTrombone'],['BassTrombone'],['Timpani'],['Violins1'],['Violins2'],['Violas'],['Cellos'],['Basses']]
def frac(text): return float(Fraction(text or '0'))

def preset_catalog(directory):
    result={}
    for path in sorted(directory.glob('*.json')):
        data=json.loads(path.read_text(encoding='utf-8'))
        root=data['data']['custom']['sampler']['rootNode']; branches=[]
        for i,node in enumerate(root.get('nodes',[])):
            leaves=[]
            def walk(n,indices,titles):
                if n.get('patchName'): leaves.append({'node_path':indices,'titles':titles,'patch_name':n['patchName']})
                for j,child in enumerate(n.get('nodes',[])): walk(child,indices+[j],titles+[child.get('title','')])
            walk(node,[i],[node.get('title','')]); branches.append({'index':i,'title':node.get('title',''),'leaves':leaves})
        bytitle={b['title'].lower():b['index'] for b in branches}; mapping={}
        for art,titles in {'sustain':['long notes','single strokes'],'staccato':['staccato','short notes','single strokes'],'legato':['legato'],'pizzicato':['pizzicato'],'tremolo':['tremolo','rolls']}.items(): mapping[art]=next((bytitle[t] for t in titles if t in bytitle),None)
        result[path.stem]={'file':path.as_posix(),'root_branches':branches,'articulation_root_indices':mapping,'keyswitch_midi_notes':None}
    return result

def parse_score(path):
    staves=ET.parse(path).getroot().find('Score').findall('Staff')
    starts=[]; lengths=[]; q=0.; meter=3.
    for measure in staves[0].findall('Measure'):
        ts=measure.find('.//TimeSig')
        if ts is not None: meter=4*int(ts.findtext('sigN'))/int(ts.findtext('sigD'))
        length=4*frac(measure.get('len')) if measure.get('len') else meter
        starts.append(q); lengths.append(length); q+=length
    notes=[]; events=[]; slurs=[]
    for staff in staves:
        sid=int(staff.get('id'))
        for mi,measure in enumerate(staff.findall('Measure')):
            for vi,voice in enumerate(measure.findall('voice')):
                pos=0.; tuplets=[]
                for e in voice:
                    tag=e.tag; on=starts[mi]+pos
                    if tag=='location': pos+=4*frac(e.findtext('fractions')); continue
                    if tag=='Tuplet': tuplets.append(int(e.findtext('normalNotes','2'))/int(e.findtext('actualNotes','3'))); continue
                    if tag=='endTuplet':
                        if tuplets: tuplets.pop()
                        continue
                    if tag in ('StaffText','SystemText','Text','PlayingTechnique'):
                        text=''.join(e.find('text').itertext()).strip() if e.find('text') is not None else ''
                        if text: events.append({'staff':sid,'voice':vi,'onset_q':on,'type':'text','text':text})
                        continue
                    if tag not in ('Chord','Rest'): continue
                    dtype=e.findtext('durationType','quarter'); dur=(4*frac(e.findtext('duration')) or lengths[mi]) if dtype=='measure' else DUR.get(dtype,1)
                    dur*=2-2**(-int(e.findtext('dots','0')))
                    for factor in tuplets: dur*=factor
                    grace=any(e.find(t) is not None for t in ('acciaccatura','appoggiatura','grace4','grace16','grace32'))
                    marks=[a.findtext('subtype','') for a in e.findall('Articulation')]; trem=e.findtext('Tremolo/subtype')
                    for sp in e.findall('Spanner'):
                        loc=sp.find('next/location')
                        if sp.get('type')=='Slur' and loc is not None:
                            endmi=mi+int(loc.findtext('measures','0'))
                            if 0<=endmi<len(starts): slurs.append({'staff':sid,'voice':vi,'onset_q':on,'end_q':starts[endmi]+pos+4*frac(loc.findtext('fractions')),'type':'slur'})
                    if tag=='Chord':
                        for n in e.findall('Note'): notes.append({'staff':sid,'voice':vi,'measure':mi+1,'onset_q':on,'duration_q':dur,'pitch':int(n.findtext('pitch')),'marks':marks,'tremolo':trem,'grace':grace,'tie_in':n.find("Spanner[@type='Tie']/prev") is not None})
                        for mark in marks: events.append({'staff':sid,'voice':vi,'onset_q':on,'type':'articulation','subtype':mark})
                        if trem: events.append({'staff':sid,'voice':vi,'onset_q':on,'end_q':on+dur,'type':'tremolo','subtype':trem})
                    if not grace: pos+=dur
    texts=defaultdict(list)
    for e in sorted(events,key=lambda e:e['onset_q']):
        if e['type']=='text': texts[e['staff']].append(e)
    for n in notes:
        mode='arco'
        for e in texts[n['staff']]:
            if e['onset_q']>n['onset_q']+1e-7: break
            t=e['text'].lower().strip()
            if t in ('pizz','pizz.'): mode='pizzicato'
            elif t=='arco': mode='arco'
        under=any(s['staff']==n['staff'] and s['voice']==n['voice'] and s['onset_q']-1e-7<=n['onset_q']<=s['end_q']+1e-7 for s in slurs)
        if mode=='pizzicato': art,reason='pizzicato','explicit persistent pizz text'
        elif n['tremolo']: art,reason='tremolo','explicit Tremolo subtype'
        elif any('stacc' in x.lower() for x in n['marks']): art,reason='staccato','explicit staccato/staccatissimo'
        elif under: art,reason='legato','inclusive XML slur span'
        else: art,reason='sustain','unmarked default; preserve MIDI gate'
        n.update(articulation=art,reason=reason)
    return notes,events+slurs,{'measure_starts_q':starts,'score_end_q':q}

def read_midi(path):
    midi=mido.MidiFile(path); notes=[]
    for i,track in enumerate(midi.tracks):
        tick=0; active=defaultdict(list); serial=0
        for msg in track:
            tick+=msg.time
            if msg.type=='note_on' and msg.velocity: active[(msg.channel,msg.note)].append((tick/midi.ticks_per_beat,msg.velocity,serial)); serial+=1
            elif msg.type=='note_off' or (msg.type=='note_on' and not msg.velocity):
                a=active[(msg.channel,msg.note)]
                if a:
                    on,vel,num=a.pop(0); off=tick/midi.ticks_per_beat
                    if off>START and on<END: notes.append({'id':f'{i+1}:{num}','staff':i+1,'onset_q':max(START,on),'offset_q':min(END,off),'source_onset_q':on,'pitch':msg.note,'velocity':vel,'source_channel':msg.channel})
    return sorted(notes,key=lambda n:(n['staff'],n['onset_q'],n['pitch'],n['id']))

def build_plan(root=None):
    root=Path(root) if root else Path(__file__).resolve().parent.parent
    xmlnotes,events,scoreinfo=parse_score(root/'work/Brahms Symphony #4 fourth movement.mscx')
    midi=read_midi(root/'work/movement4.mid'); catalog=preset_catalog(root/'render_work/presets'); bystaff=defaultdict(list)
    for n in xmlnotes: bystaff[n['staff']].append(n)
    shifts={}; evidence={}
    for sid,rows in bystaff.items():
        keys={(round(n['onset_q'],4),n['pitch']) for n in rows}
        counts={d:sum((round(n['source_onset_q'],4),n['pitch']-d) in keys for n in midi if n['staff']==sid) for d in (-24,-12,0,12,24)}
        shifts[sid]=max(counts,key=lambda d:(counts[d],d==0)); evidence[sid]=counts
    for n in midi:
        candidates=[x for x in bystaff[n['staff']] if x['pitch']+shifts[n['staff']]==n['pitch'] and x['onset_q']-.035<=n['source_onset_q']<x['onset_q']+x['duration_q']-1e-7]
        ornament_match=False
        if not candidates:
            candidates=[x for x in bystaff[n['staff']] if 'ornamentTrill' in x['marks'] and x['onset_q']<=n['source_onset_q']<x['onset_q']+x['duration_q'] and abs(x['pitch']-n['pitch'])<=2]
            ornament_match=bool(candidates)
        x=min(candidates,key=lambda x:abs(x['onset_q']-n['source_onset_q'])) if candidates else None
        art=x['articulation'] if x else 'sustain'
        if x and n['staff']==11 and 'ornamentTrill' in x['marks']: art='tremolo'
        n['xml_pitch']=x['pitch'] if x else None
        n['ornament_expansion']=ornament_match
        n['timpani_trill_as_roll_approximation']=bool(x and n['staff']==11 and 'ornamentTrill' in x['marks'])
        n.update(articulation=art,xml_match='ornament_expansion' if ornament_match else ('onset' if x and abs(x['onset_q']-n['source_onset_q'])<.035 else ('within_duration' if x else 'unmatched')),xml_onset_q=x['onset_q'] if x else None,xml_voice=x['voice'] if x else None,measure=x['measure'] if x else None,reason=x['reason'] if x else 'unmatched MIDI note; conservative sustain',excerpt_onset_q=n['onset_q']-START,performance_nominal_on_tick=round((n['onset_q']-START+PRE)*TPQ),performance_nominal_off_tick=round((n['offset_q']-START+PRE)*TPQ))
        n['preset_options']=[{'preset':p,'root_index':catalog[p]['articulation_root_indices'].get(art),'fallback_root_index':catalog[p]['articulation_root_indices']['sustain']} for p in PRESETS[n['staff']-1]]
    return {'schema':'brahms-articulation-plan-v1','source_range_q':[START,END],'range_end_exclusive':True,'timing':{'performance_tpq':TPQ,'preroll_q':PRE,'source_q_to_nominal_tick':'round((q - 384 + 1.5) * 960)','humanization':'prepare_performance.py adds shared-onset random +/-4ms offsets; these ticks precede that shift','seconds':'Use performance_manifest tempo_points, not fixed BPM.'},'presets':catalog,'notes':midi,'lane_events':[{k:n[k] for k in ('staff','onset_q','pitch','id','articulation')} for n in midi],'notation_events':[e for e in events if e.get('end_q',e['onset_q'])>=START and e['onset_q']<END],'inherited_text_events':[e for e in events if e['type']=='text' and e['onset_q']<START and e['text'].lower().strip() in ('pizz','pizz.','arco')],'xml_notes':[n for n in xmlnotes if START<=n['onset_q']<END],'audit':{'midi_note_count':len(midi),'staff_counts':dict(Counter(n['staff'] for n in midi)),'articulations':dict(Counter(n['articulation'] for n in midi)),'match_counts':dict(Counter(n['xml_match'] for n in midi)),'xml_to_midi_pitch_shift':shifts,'pitch_shift_exact_match_evidence':evidence,'score_end_q':scoreinfo['score_end_q'],'measure113_q':scoreinfo['measure_starts_q'][112]},'limitations':['Slur assignment includes endpoints; sample legato needs audition and monophonic player splitting.','MIDI ornaments/tremolos can expand one XML note into many attacks. No attacks added, removed or merged.','Mixed divisi text retained verbatim; only exact pizz/pizz./arco updates staff-wide bow mode.','No duration-only staccato inference: explicit notation wins; unmarked notes sustain with existing MIDI gate.','Root indices are JSON node offsets, never MIDI keyswitch numbers. Short-notes branches contain multiple sub-articulations; inspect leaf paths.','No acoustic validation claimed.']}

def main():
    root=Path(__file__).resolve().parent.parent; plan=build_plan(root)
    (root/'render_work/articulation_plan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
    print(json.dumps(plan['audit'],indent=2))
if __name__=='__main__': main()
