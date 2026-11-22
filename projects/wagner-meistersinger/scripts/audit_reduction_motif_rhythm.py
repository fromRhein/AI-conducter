from pathlib import Path
import xml.etree.ElementTree as ET

src = Path(__file__).with_name('digital') / 'Buelow_reference.musicxml'
root = ET.parse(src).getroot()

def child(el, name):
    return next((x for x in el if x.tag.rsplit('}', 1)[-1] == name), None)
def text(el, name, default=''):
    x = child(el, name)
    return x.text if x is not None and x.text is not None else default

for measure in (e for e in root.iter() if e.tag.rsplit('}', 1)[-1] == 'measure'):
    try:
        number = int(measure.get('number', '0'))
    except ValueError:
        continue
    if number not in (89, 91, 93, 95, 121, 150):
        continue
    cursor = last_onset = 0
    events = []
    for note in (e for e in measure if e.tag.rsplit('}', 1)[-1] == 'note' and text(e, 'voice', '1') == '1'):
        chord = child(note, 'chord') is not None
        onset = last_onset if chord else cursor
        duration = int(text(note, 'duration', '0'))
        pitch = child(note, 'pitch')
        if pitch is None:
            label = 'REST'
        else:
            step = text(pitch, 'step')
            alter = int(float(text(pitch, 'alter', '0')))
            octave = int(text(pitch, 'octave', '4'))
            label = step + ('#' if alter == 1 else 'b' if alter == -1 else '') + str(octave)
        events.append((onset, duration, label, 'chord' if chord else ''))
        if not chord:
            last_onset = onset
            cursor += duration
    print('measure', number, events)
