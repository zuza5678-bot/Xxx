import numpy as np, wave, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from timeline import build, S
TL, TOTAL = build()
SR = 44100
N = int((TOTAL + 2) * SR)
L = np.zeros(N); R = np.zeros(N)
rng = np.random.default_rng(7)
def m2f(m): return 440 * 2 ** ((m - 69) / 12)
def add(buf, start, sig):
    i = int(start * SR)
    if i >= N: return
    sig = sig[:N - i]; buf[i:i + len(sig)] += sig
def env(n, a, r, sus=1.0):
    e = np.ones(n) * sus
    na, nr = int(a * SR), int(r * SR)
    e[:na] = np.linspace(0, sus, na) ** 1.5
    e[-nr:] *= np.linspace(1, 0, nr) ** 2
    return e
BAR = 60 / 72 * 4
PROG = [[50, 53, 57, 62], [46, 50, 53, 58], [53, 57, 60, 65], [48, 52, 55, 60]]
ROOT = [38, 34, 41, 36]
def scene_at(t):
    for s in TL:
        if s['start'] <= t < s['end']: return s['key']
    return 'outro'
DARK = {'1772', '1795', '1939'}
def pad(notes, dur, bright):
    n = int((dur + 1.6) * SR); t = np.arange(n) / SR
    out_l = np.zeros(n); out_r = np.zeros(n)
    for m in notes:
        f0 = m2f(m)
        for det, pan in ((-0.07, 0.2), (0.0, 0.5), (0.08, 0.8)):
            f = f0 * 2 ** (det / 12)
            ph = rng.uniform(0, 2 * np.pi)
            s = np.zeros(n)
            for k in range(1, 11):
                if f * k > 9000: break
                s += np.sin(2 * np.pi * f * k * t + ph * k) / k * np.exp(-k / bright)
            s *= 1 + 0.15 * np.sin(2 * np.pi * 4.8 * t + ph)  # gentle vibrato-ish tremolo
            out_l += s * (1 - pan); out_r += s * pan
    e = env(n, 0.9, 1.6)
    return out_l * e, out_r * e
t_bar = 0.0; bi = 0
while t_bar < TOTAL + 1:
    k = scene_at(t_bar + 0.1)
    if k == 'outro' and t_bar > TL[-1]['start'] + 0.5:
        notes, root = [50, 54, 57, 62, 66], 38
    else:
        notes, root = PROG[bi % 4], ROOT[bi % 4]
    bright = 2.2 if k in DARK else (3.5 if k in ('intro',) else 4.5)
    vol = 0.05 if k == 'intro' else 0.065
    pl, pr = pad(notes, BAR, bright); add(L, t_bar, pl * vol); add(R, t_bar, pr * vol)
    # bass
    n = int((BAR + 1.0) * SR); tt = np.arange(n) / SR; f = m2f(root)
    b = (np.sin(2 * np.pi * f * tt) + 0.35 * np.sin(4 * np.pi * f * tt) + 0.12 * np.sin(6 * np.pi * f * tt)) * env(n, 0.3, 1.0)
    bv = 0.0 if k == 'intro' and t_bar < 4 else 0.11
    add(L, t_bar, b * bv); add(R, t_bar, b * bv)
    # pulse ostinato (eighths)
    if k not in DARK and k != 'intro' and not (k == 'outro' and t_bar > TL[-1]['start'] + 2):
        step = BAR / 8
        for j in range(8):
            m = root + 12 + (12 if j % 4 == 2 else 0) + (7 if j % 8 == 5 else 0)
            n = int(0.45 * SR); tt = np.arange(n) / SR; f = m2f(m)
            s = sum(np.sin(2 * np.pi * f * h * tt) / h * np.exp(-h / 2.5) for h in range(1, 6)) * np.exp(-tt * 9)
            acc = 1.0 if j % 2 == 0 else 0.65
            pan = 0.35 if j % 2 else 0.65
            add(L, t_bar + j * step, s * 0.05 * acc * (1 - pan) * 2); add(R, t_bar + j * step, s * 0.05 * acc * pan * 2)
    elif k in DARK:
        # low heartbeat
        for j in (0, 0.28, 2.0 * BAR / 4 * 2 / 2, 2.0 * BAR / 4 * 2 / 2 + 0.28):
            n = int(0.5 * SR); tt = np.arange(n) / SR
            s = np.sin(2 * np.pi * (48 - 12 * tt) * tt) * np.exp(-tt * 10)
            add(L, t_bar + j, s * 0.18); add(R, t_bar + j, s * 0.18)
    t_bar += BAR; bi += 1
# timpani hits + risers at scene starts
for s in TL[1:]:
    t0 = s['start']
    n = int(2.0 * SR); tt = np.arange(n) / SR
    f = 62 * (1 + 0.5 * np.exp(-tt * 18))
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 2.6)
    noise = rng.standard_normal(n) * np.exp(-tt * 30) * 0.25
    hit = (boom + noise) * (0.42 if s['key'] in ('1918', '1945', 'outro', '966') else 0.3)
    add(L, t0, hit); add(R, t0, hit)
    # riser
    n = int(1.0 * SR); tt = np.arange(n) / SR
    nz = rng.standard_normal(n)
    # crude band shaping: moving average
    nz = np.convolve(nz, np.ones(12) / 12, mode='same')
    r = nz * (tt / 1.0) ** 2.5 * 0.08
    add(L, t0 - 1.0, r); add(R, t0 - 1.0, r[::-1] * 0 + r)
# reverb
def ir(seed):
    g = np.random.default_rng(seed); n = int(2.8 * SR); tt = np.arange(n) / SR
    x = g.standard_normal(n) * np.exp(-tt * 2.4)
    x = np.convolve(x, np.ones(6) / 6, mode='same'); x[:int(0.02 * SR)] = 0
    return x / np.sqrt((x ** 2).sum())
def conv(x, h):
    m = len(x) + len(h); nfft = 1 << (m - 1).bit_length()
    return np.fft.irfft(np.fft.rfft(x, nfft) * np.fft.rfft(h, nfft), nfft)[:len(x)]
WL = L + 0.45 * conv(L, ir(1)) * 0.9; WR = R + 0.45 * conv(R, ir(2)) * 0.9
# fade out end
fo = int(2.5 * SR); end = int(TOTAL * SR)
for b in (WL, WR):
    b[end - fo:end] *= np.linspace(1, 0, fo); b[end:] = 0
st = np.stack([WL, WR], 1); st /= np.abs(st).max() * 1.12
with wave.open(f'{S}/music.wav', 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((st * 32767).astype(np.int16).tobytes())
print('music ok', TOTAL)
