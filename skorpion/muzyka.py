"""Syntetyczna ścieżka dźwiękowa do rolki "Skorpion" (27 s, 44.1 kHz, stereo)."""
import wave
import numpy as np

SR = 44100
DUR = 27.0
N = int(SR * DUR)
L = np.zeros(N)
R = np.zeros(N)
BEAT = 0.5  # 120 BPM


def note_freq(n):  # n: półtony względem A4
    return 440.0 * 2 ** (n / 12)


def add(sig, t0, pan=0.0, gain=1.0):
    i0 = int(t0 * SR)
    if i0 >= N:
        return
    sig = sig[: N - i0] * gain
    L[i0:i0 + len(sig)] += sig * (1 - pan) * 0.5 * 2 ** 0.5 if pan > 0 else sig * 0.707
    R[i0:i0 + len(sig)] += sig * (1 + pan) * 0.5 * 2 ** 0.5 if pan < 0 else sig * 0.707


def env(n, a=0.005, d=0.2):
    t = np.arange(n) / SR
    e = np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / d)
    return e


def kick(gain=1.0):
    n = int(0.45 * SR)
    t = np.arange(n) / SR
    f = 45 + 110 * np.exp(-t * 30)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-t * 7) * gain


def snare():
    n = int(0.25 * SR)
    t = np.arange(n) / SR
    noise = np.random.randn(n)
    noise = noise - np.convolve(noise, np.ones(6) / 6, "same")  # prosty górnoprzepust
    return (noise * 0.6 + np.sin(2 * np.pi * 190 * t) * 0.5) * np.exp(-t * 18)


def hat(dec=40):
    n = int(0.08 * SR)
    t = np.arange(n) / SR
    noise = np.random.randn(n)
    noise = noise - np.convolve(noise, np.ones(3) / 3, "same")
    return noise * np.exp(-t * dec) * 0.35


def saw(freq, dur, cutoff_smooth=8):
    n = int(dur * SR)
    t = np.arange(n) / SR
    s = 2 * ((t * freq) % 1) - 1
    k = np.ones(cutoff_smooth) / cutoff_smooth
    return np.convolve(s, k, "same")


def bass(n_semi, dur):
    f = note_freq(n_semi)
    s = saw(f, dur, 14) * 0.7 + np.sin(2 * np.pi * f * np.arange(int(dur * SR)) / SR) * 0.6
    return s * env(len(s), 0.004, dur * 0.6)


def pluck(n_semi, dur=0.35):
    f = note_freq(n_semi)
    n = int(dur * SR)
    t = np.arange(n) / SR
    s = np.sin(2 * np.pi * f * t) + 0.4 * np.sin(4 * np.pi * f * t) + 0.15 * np.sin(6 * np.pi * f * t)
    return s * env(n, 0.002, 0.12) * 0.5


def pad(semis, dur, gain=0.18):
    n = int(dur * SR)
    t = np.arange(n) / SR
    s = np.zeros(n)
    for k, sm in enumerate(semis):
        f = note_freq(sm)
        for det in (-0.3, 0.3):
            s += saw(f + det, dur, 30)
    s /= len(semis) * 2
    fade = np.minimum(1, t / 1.2) * np.minimum(1, (dur - t) / 1.0)
    lfo = 0.75 + 0.25 * np.sin(2 * np.pi * 0.25 * t)
    return s * fade * lfo * gain


def boom():
    n = int(2.5 * SR)
    t = np.arange(n) / SR
    f = 30 + 80 * np.exp(-t * 6)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 1.6)
    nz = np.random.randn(n)
    nz = np.convolve(nz, np.ones(40) / 40, "same") * np.exp(-t * 3) * 3
    return (s + nz) * 1.1


def riser(dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    nz = np.random.randn(n)
    nz = nz - np.convolve(nz, np.ones(4) / 4, "same")
    f = 200 + 1200 * (t / dur) ** 2
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.3
    return (nz * 0.25 + tone) * (t / dur) ** 2


# Skala frygijska dominantowa od A ("pustynny" klimat): A Bb C# D E F G
A2, A3 = -24, -12
SCALE = [0, 1, 4, 5, 7, 8, 10, 12]

# --- 0-7 s: noc na pustyni (pad + ciche tykanie)
add(pad([A2, A2 + 7, A3 + 3], 7.5, 0.22), 0.0)
for i in range(14):
    add(hat(60), 0.25 + i * BEAT, pan=0.4 if i % 2 else -0.4, gain=0.5)
for i, s in enumerate([0, 1, 4, 1, 0, 5, 4, 1]):
    add(pluck(A3 + 12 + s, 0.6), 1.0 + i * 0.75, pan=-0.3 + 0.08 * i, gain=0.5)

# --- 7-10 s: napięcie (bicie serca przyspiesza + riser)
t = 7.0
gap = 0.6
while t < 9.9:
    add(kick(0.8), t)
    add(kick(0.5), t + 0.15)
    t += gap
    gap = max(0.28, gap * 0.85)
add(riser(3.0), 7.0, gain=0.7)
add(pad([A2, A2 + 1], 3.0, 0.2), 7.0)

# --- 10 s: uderzenie "SKORPION!"
add(boom(), 10.0, gain=0.9)
add(snare(), 10.0, gain=0.8)

# --- 10.5-16 s: groźny ostinato
pattern = [0, 0, 12, 0, 1, 0, 7, 5]
t = 10.5
k = 0
while t < 16.0 - 1e-6:
    add(bass(A2 + pattern[k % 8], BEAT / 2), t, gain=0.55)
    if k % 2 == 0:
        add(kick(), t)
    add(hat(), t + BEAT / 4, pan=0.3, gain=0.6)
    t += BEAT / 2
    k += 1

# --- 16-21 s: pościg (szybszy bas, werbel, arpeggio)
t = 16.0
k = 0
arp = [0, 4, 7, 12, 8, 7, 4, 1]
while t < 21.0 - 1e-6:
    add(bass(A2 + (0 if (k // 8) % 2 == 0 else 1), BEAT / 4), t, gain=0.5)
    if k % 4 == 0:
        add(kick(), t)
    if k % 8 == 4:
        add(snare(), t, gain=0.7)
    add(hat(70), t, pan=-0.3 if k % 2 else 0.3, gain=0.45)
    if k % 2 == 0:
        add(pluck(A3 + 12 + arp[(k // 2) % 8], 0.25), t, pan=0.25, gain=0.55)
    t += BEAT / 4
    k += 1
add(riser(1.0), 20.0, gain=0.5)

# --- 21-24 s: oddech, "bezpieczny... chyba"
add(snare(), 21.0, gain=0.6)
add(kick(), 21.0)
add(pad([A2, A2 + 7, A3 + 4], 3.2, 0.2), 21.0)
for i, s in enumerate([12, 8, 7, 4, 5, 4]):
    add(pluck(A3 + s, 0.5), 21.3 + i * 0.45, gain=0.5)

# --- 24-27 s: zakończenie
add(kick(), 24.0)
add(pad([A2, A2 + 7, A3 + 1, A3 + 4], 3.0, 0.28), 24.0)
for i, s in enumerate([0, 4, 7, 12]):
    add(pluck(A3 + 12 + s, 1.5), 24.0 + i * 0.12, gain=0.45)

# prosty pogłos (kilka echa)
for buf in (L, R):
    dry = buf.copy()
    for d, g in ((0.113, 0.28), (0.197, 0.2), (0.31, 0.14), (0.47, 0.09)):
        k = int(d * SR)
        buf[k:] += dry[:-k] * g

mix = np.stack([L, R], axis=1)
mix /= np.max(np.abs(mix)) + 1e-9
mix *= 0.89
# łagodne wyciszenie na końcu
fade = int(1.2 * SR)
mix[-fade:] *= np.linspace(1, 0, fade)[:, None]

pcm = (mix * 32767).astype(np.int16)
with wave.open("muzyka.wav", "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print("muzyka.wav gotowa")
