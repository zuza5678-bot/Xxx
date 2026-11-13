import json, os, wave, sys, re
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from scenes import SCENES
from piper import PiperVoice, SynthesisConfig
S='/tmp/claude-0/-home-user-Xxx/30a8b2ec-cf16-5359-8239-efaca9b7059f/scratchpad'
os.makedirs(f'{S}/tts', exist_ok=True)
voice = PiperVoice.load(f'{S}/voice/pl-mls_6892-low.onnx')
cfg = SynthesisConfig(length_scale=1.14, noise_scale=0.55, noise_w_scale=0.6)
sr = voice.config.sample_rate
out = {}
for sc in SCENES:
    for i, (cap, spk) in enumerate(sc['lines']):
        parts = [p for p in re.split(r'(?<=[.,])\s+', spk) if p.strip()]
        audio = []
        for j, p in enumerate(parts):
            a = np.concatenate([np.frombuffer(c.audio_int16_bytes, np.int16) for c in voice.synthesize(p, syn_config=cfg)])
            # trim leading/trailing silence
            idx = np.where(np.abs(a) > 300)[0]
            a = a[max(0, idx[0]-int(.03*sr)): idx[-1]+int(.06*sr)]
            audio.append(a)
            if j < len(parts)-1:
                audio.append(np.zeros(int(sr*(0.32 if p.endswith('.') else 0.12)), np.int16))
        a = np.concatenate(audio)
        fn = f"{S}/tts/{sc['key']}_{i}.wav"
        with wave.open(fn, 'wb') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(a.tobytes())
        out[f"{sc['key']}_{i}"] = len(a)/sr
        print(sc['key'], i, round(len(a)/sr,2), [p for p in parts])
json.dump(out, open(f'{S}/tts/durations.json','w'), indent=1)
print('total', sum(out.values()))
