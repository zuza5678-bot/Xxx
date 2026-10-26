"""Zapasowa muzyka do rolki: ciemny, minimalistyczny podkład (fortepian, smyczki, puls serca),
który po ~17 s rozjaśnia się do ciepłej, pełnej nadziei harmonii.

Uruchomienie:  python3 music.py  ->  assets/music_synth.wav
"""
import os
import wave

import numpy as np

SR = 44100
DUR = 27.0
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "assets", "music_synth.wav")
TURN = 17.0   # moment przejścia w nadzieję (scena 4)


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def piano(m, length, vel=1.0):
    n = int(length * SR)
    t = np.arange(n) / SR
    f = hz(m)
    sig = np.zeros(n)
    for k, amp in enumerate((1.0, 0.5, 0.28, 0.15, 0.08, 0.04), start=1):
        inh = f * k * (1 + 0.0004 * k * k)
        sig += amp * np.sin(2 * np.pi * inh * t) * np.exp(-t * (1.2 + k * 0.9))
    att = np.minimum(t / 0.004, 1)
    return (sig * att * vel * 0.25).astype(np.float32)


def strings(ms, length, vol):
    n = int(length * SR)
    t = np.arange(n) / SR
    sig = np.zeros(n)
    for m in ms:
        for det in (-0.12, 0.0, 0.12):
            f = hz(m + det)
            vib = 1 + 0.003 * np.sin(2 * np.pi * 5.2 * t)
            sig += np.sin(2 * np.pi * f * t * vib) + 0.3 * np.sin(4 * np.pi * f * t * vib)
    env = np.minimum(t / 1.5, 1) * np.minimum((length - t) / 1.5, 1)
    return (sig * env * vol / len(ms)).astype(np.float32)


def main():
    n = int(DUR * SR)
    out = np.zeros(n, np.float32)
    rng = np.random.default_rng(3)

    def add(sig, t0, g=1.0):
        i = int(t0 * SR)
        j = min(n, i + len(sig))
        if i < n:
            out[i:j] += sig[: j - i] * g

    # część mroczna: d-moll, rzadkie dźwięki fortepianu, niski dron i puls serca
    dark = [(0.0, [50, 57, 62]), (4.0, [46, 53, 58]), (8.0, [48, 55, 60]), (12.0, [45, 52, 57])]
    melody_dark = [(1.0, 74), (2.5, 72), (3.2, 69), (5.0, 70), (6.5, 69), (9.0, 67),
                   (10.5, 69), (11.2, 65), (13.0, 64), (14.5, 65), (15.5, 64)]
    for t0, ch in dark:
        add(strings([c - 12 for c in ch], 5.0, 0.18), t0)
        add(piano(ch[0] - 12, 4.0, 0.9), t0)
    for t0, m in melody_dark:
        add(piano(m, 3.0, 0.55), t0)
    hb = np.arange(int(0.18 * SR)) / SR
    beat = (np.sin(2 * np.pi * 48 * hb) * np.exp(-hb * 22)).astype(np.float32)
    t = 2.0
    while t < TURN - 0.5:
        add(beat, t, 0.55)
        add(beat, t + 0.28, 0.35)
        t += 1.05

    # akcent przy "TO JEST MOBBING." i cisza przed zmianą
    add(piano(38, 4.0, 1.4), 15.6)
    add(piano(45, 4.0, 1.0), 15.6)

    # nadzieja: F-dur / C-dur / d-moll / B-dur, cieplejsze smyczki i jaśniejsza melodia
    bright = [(TURN, [53, 60, 65, 69]), (TURN + 2.5, [48, 55, 64, 67]),
              (TURN + 5.0, [50, 57, 62, 65]), (TURN + 7.5, [46, 53, 62, 65])]
    for t0, ch in bright:
        add(strings(ch, 3.6, 0.22), t0)
        for k, m in enumerate(ch):
            add(piano(m, 3.0, 0.45), t0 + k * 0.18)
    melody = [(0.4, 72), (1.2, 74), (1.8, 77), (3.0, 76), (3.6, 72), (5.4, 74), (6.0, 77),
              (6.6, 81), (8.0, 79), (8.6, 77)]
    for dt, m in melody:
        add(piano(m, 2.5, 0.6), TURN + dt)

    # prosty pogłos: kilka opóźnionych, wytłumionych kopii
    rev = out.copy()
    for d, g in ((0.031, 0.35), (0.047, 0.3), (0.071, 0.25), (0.113, 0.2), (0.167, 0.15), (0.241, 0.1)):
        k = int(d * SR)
        rev[k:] += out[:-k] * g
    out = rev + rng.normal(0, 0.0015, n).astype(np.float32)
    fo = int(2.0 * SR)
    out[-fo:] *= np.linspace(1, 0, fo)
    out /= np.abs(out).max() / 0.8
    stereo = np.stack([out, np.roll(out, int(0.012 * SR))], axis=1)
    with wave.open(OUT, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes((stereo * 32767).astype(np.int16).tobytes())
    print("Gotowe:", OUT)


if __name__ == "__main__":
    main()
