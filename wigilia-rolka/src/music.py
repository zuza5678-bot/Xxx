"""Original lo-fi Christmas backing track, synthesized with numpy.
Usage: python music.py <duration_s> <quiet_start> <quiet_end> out.wav
"""
import sys, wave
import numpy as np

SR = 44100
dur, q0, q1, out = float(sys.argv[1]), float(sys.argv[2]), float(sys.argv[3]), sys.argv[4]
N = int(dur * SR)
L = np.zeros(N); R = np.zeros(N)
rng = np.random.default_rng(7)
BPM = 84.0
beat = 60.0 / BPM
bar = 4 * beat

def hz(m): return 440.0 * 2 ** ((m - 69) / 12)

def add(sig, t0, pan=0.0, gain=1.0):
    i = int(t0 * SR)
    if i >= N: return
    sig = sig[: N - i] * gain
    L[i:i + len(sig)] += sig * np.sqrt(0.5 * (1 - pan))
    R[i:i + len(sig)] += sig * np.sqrt(0.5 * (1 + pan))

def bell(m, length=1.6):
    t = np.arange(int(length * SR)) / SR
    f = hz(m)
    s = (np.sin(2*np.pi*f*t) * np.exp(-t*3.2)
         + 0.35*np.sin(2*np.pi*f*2.76*t) * np.exp(-t*7)
         + 0.15*np.sin(2*np.pi*f*5.4*t) * np.exp(-t*12))
    s *= np.minimum(1, t / 0.003)
    return s

def pad(m, length):
    t = np.arange(int(length * SR)) / SR
    s = np.zeros_like(t)
    for det in (-0.12, 0.0, 0.11):
        f = hz(m + det)
        for h in range(1, 7):
            s += np.sin(2*np.pi*f*h*t + h) / (h ** 1.6)
    env = np.minimum(1, t / 0.6) * np.minimum(1, (length - t) / 0.5)
    return s * env * 0.06

def kick():
    t = np.arange(int(0.45 * SR)) / SR
    f = 45 + 80 * np.exp(-t * 28)
    ph = 2*np.pi*np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-t * 7)

def hat(open_=False):
    n = int((0.18 if open_ else 0.05) * SR)
    x = rng.standard_normal(n)
    x = np.diff(x, prepend=0)  # crude high-pass
    t = np.arange(n) / SR
    return x * np.exp(-t * (18 if open_ else 70)) * 0.25

def sleigh():
    n = int(0.12 * SR)
    t = np.arange(n) / SR
    x = np.diff(np.diff(rng.standard_normal(n), prepend=0), prepend=0)
    x *= (0.6 + 0.4*np.sin(2*np.pi*38*t))
    return x * np.exp(-t * 30) * 0.05

def bass(m, length):
    t = np.arange(int(length * SR)) / SR
    f = hz(m)
    s = np.sin(2*np.pi*f*t) + 0.25*np.sin(4*np.pi*f*t)
    return s * np.minimum(1, t/0.01) * np.exp(-t*1.2) * np.minimum(1, (length-t)/0.05)

# Cmaj7 - Am7 - Fmaj7 - G6(sus)  (MIDI notes)
prog = [
    (48, [60, 64, 67, 71]),
    (45, [57, 60, 64, 67]),
    (41, [57, 60, 65, 69]),
    (43, [59, 62, 67, 69]),
]
arp_pat = [0, 2, 1, 3, 2, 1, 3, 2]

def in_quiet(t): return q0 <= t < q1

nbars = int(dur / bar) + 1
for b in range(nbars):
    t0 = b * bar
    root, ch = prog[b % 4]
    final = t0 >= dur - bar * 1.2
    if final:
        root, ch = prog[0]
    # pad
    add(pad(ch[0], bar + 0.6) + pad(ch[1], bar + 0.6) + pad(ch[2], bar + 0.6) + pad(ch[3], bar + 0.6), t0, 0, 1.0)
    for k in range(8):
        tt = t0 + k * beat / 2
        if tt >= dur: break
        q = in_quiet(tt)
        # bells arpeggio (an octave up)
        m = ch[arp_pat[k]] + 12
        add(bell(m), tt, pan=(-0.4 if k % 2 else 0.4), gain=0.16 if not q else 0.10)
        if final: continue
        # drums enter on bar 2, drop during quiet section
        if b >= 1 and not q:
            if k in (0, 5):
                add(kick(), tt, 0, 0.55)
            if k in (2, 6):  # soft snare-ish noise
                n = int(0.2*SR); tn = np.arange(n)/SR
                add(rng.standard_normal(n)*np.exp(-tn*22)*0.12, tt, 0.1)
            add(hat(open_=(k == 7)), tt, 0.3, 0.6)
            add(sleigh(), tt + beat/4, -0.3)
            add(sleigh(), tt, -0.3, 0.7)
    if not in_quiet(t0) and b >= 1 and not final:
        add(bass(root, beat * 2), t0, 0, 0.32)
        add(bass(root, beat * 2), t0 + beat * 2, 0, 0.28)

# final ringing chord
fin_t = max(0, dur - bar * 1.2)
for m in (60, 64, 67, 71, 72, 76):
    add(bell(m + 12, 3.0), fin_t + 0.05 * (m % 5), 0, 0.12)

# light vinyl crackle
crk = np.zeros(N)
idx = rng.integers(0, N, int(dur * 25))
crk[idx] = rng.uniform(-0.25, 0.25, len(idx))
L += crk * 0.08; R += crk * 0.08

# master: fade in/out, soft clip
env = np.minimum(1, np.arange(N) / (0.8 * SR)) * np.minimum(1, (N - np.arange(N)) / (2.0 * SR))
st = np.stack([L, R], 1) * env[:, None]
st = np.tanh(st * 1.3)
st /= np.max(np.abs(st)) + 1e-9
st *= 0.85
with wave.open(out, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((st * 32767).astype(np.int16).tobytes())
print("music ok", dur)
