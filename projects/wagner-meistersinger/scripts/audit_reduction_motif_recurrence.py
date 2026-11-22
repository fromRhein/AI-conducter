from pathlib import Path
import xml.etree.ElementTree as ET

src = Path(__file__).with_name('digital') / 'Buelow_reference.musicxml'
root = ET.parse(src).getroot()

def child(el, name):
    return next((x for x in el if x.tag.rsplit('}', 1)[-1] == name), None)

def text(el, name, default=''):
    x = child(el, name)
    return x.text if x is not None and x.text is not None else default

measures = [e for e in root.iter() if e.tag.rsplit('}', 1)[-1] == 'measure']
by_voice = {}
for measure in measures:
    cursor = 0
    last_onset = 0
    number = measure.get('number', '?')
    for note in (e for e in measure if e.tag.rsplit('}', 1)[-1] == 'note'):
        chord = child(note, 'chord') is not None
        onset = last_onset if chord else cursor
        voice = text(note, 'voice', '1')
        pitch = child(note, 'pitch')
        if pitch is not None:
            step = text(pitch, 'step')
            alter = int(float(text(pitch, 'alter', '0')))
            octave = int(text(pitch, 'octave', '4'))
            pc = {'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}[step] + alter
            midi = (octave + 1) * 12 + pc
            name = step + ('#' if alter == 1 else 'b' if alter == -1 else '') + str(octave)
            by_voice.setdefault(voice, []).append((int(number) if number.isdigit() else number, onset, midi, name))
        if not chord:
            last_onset = onset
            cursor += int(text(note, 'duration', '0'))

# m89 voice-1: C5 C5 C5 C5 D5 C5 B4 C5.
target = [72, 72, 72, 72, 74, 72, 71, 72]
print('m89 target:', target)
for voice, events in sorted(by_voice.items()):
    pitches = [e[2] for e in events]
    if voice == '1':
        for k in range(3, len(target) + 1):
            patterns = set(tuple(b-a for a,b in zip(target[s:s+k], target[s+1:s+k])) for s in range(len(target)-k+1))
            for pattern in sorted(patterns):
                hits = []
                for i in range(len(pitches)-k+1):
                    ints = tuple(b-a for a,b in zip(pitches[i:i+k], pitches[i+1:i+k]))
                    if ints == pattern and events[i][0] != 89:
                        hits.append((events[i][0], events[i][3], [e[3] for e in events[i:i+k]]))
                print('voice 1 pattern', pattern, 'length', k, 'other matches', hits[:12], 'count=', len(hits))
    print('voice', voice, 'm89 excerpt:', [e[3] for e in events if e[0] == 89][:24])
