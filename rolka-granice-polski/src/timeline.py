import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from scenes import SCENES
S='/tmp/claude-0/-home-user-Xxx/30a8b2ec-cf16-5359-8239-efaca9b7059f/scratchpad'
FPS = 30
def build():
    dur = json.load(open(f'{S}/tts/durations.json'))
    t = 0.0; out = []
    for sc in SCENES:
        k = sc['key']
        lead = 1.3 if k == 'intro' else (0.9 if k == 'outro' else 0.6)
        tail = {'intro': 0.5, '1795': 1.1, '1939': 0.9, 'outro': 3.6}.get(k, 0.55)
        lines = []; tt = t + lead
        for i, (cap, spk) in enumerate(sc['lines']):
            d = dur[f'{k}_{i}']
            lines.append({'cap': cap, 'start': tt, 'end': tt + d, 'wav': f'{S}/tts/{k}_{i}.wav'})
            tt += d + (0.35 if k != 'outro' else 0.6)
        end = lines[-1]['end'] + tail
        out.append({'key': k, 'start': t, 'end': end, 'lines': lines})
        t = end
    return out, t
if __name__ == '__main__':
    tl, T = build()
    for s in tl: print(s['key'], round(s['start'],2), round(s['end'],2))
    print('TOTAL', T)
