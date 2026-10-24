"""Animowana rolka o wiosłowaniu (9:16, 1080x1920, 30 fps) z syntezowaną muzyką.

Uruchomienie:  python3 render.py  ->  wioslowanie_rolka.mp4
Wymaga: Pillow, numpy, ffmpeg w PATH.
"""
import math
import os
import random
import subprocess
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1920
FPS = 30
DUR = 16.0
NFRAMES = int(DUR * FPS)
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "wioslowanie_rolka.mp4")

HORIZON = 1060
WATERLINE = 1200
DECK = WATERLINE - 24
STROKE_T = 2.0          # 30 uderzeń / min
T0 = 0.5                # moment pierwszego chwytu
DRIVE = 0.38            # udział fazy napędu w cyklu
S = 2                   # supersampling warstwy łodzi
PX_PER_M = 60

FONT_B = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
FONT_R = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"


def font(path, size):
    return ImageFont.truetype(path, size)


def lerp(a, b, t):
    return a + (b - a) * t


def smooth(e0, e1, x):
    t = min(max((x - e0) / (e1 - e0), 0.0), 1.0)
    return t * t * (3 - 2 * t)


def mix(c1, c2, t):
    return tuple(int(lerp(a, b, t)) for a, b in zip(c1, c2))


def hexc(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


# ---------------------------------------------------------------- tło statyczne

SKY = [(0.0, hexc("#141c3d")), (0.45, hexc("#5b3f7d")), (0.75, hexc("#e0795e")), (1.0, hexc("#fbd59a"))]
WATER = [(0.0, hexc("#e9996a")), (0.18, hexc("#9c5d78")), (0.55, hexc("#2e3560")), (1.0, hexc("#0e1430"))]
SUN = (770, HORIZON - 70)


def gradient(stops, n):
    out = np.zeros((n, 3), np.float32)
    for i in range(n):
        x = i / (n - 1)
        for (p0, c0), (p1, c1) in zip(stops, stops[1:]):
            if p0 <= x <= p1:
                t = (x - p0) / (p1 - p0)
                out[i] = np.array(c0) * (1 - t) + np.array(c1) * t
                break
    return out


def build_background():
    img = np.zeros((H, W, 3), np.float32)
    img[:HORIZON] = gradient(SKY, HORIZON)[:, None, :]
    img[HORIZON:] = gradient(WATER, H - HORIZON)[:, None, :]
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.sqrt((xx - SUN[0]) ** 2 + ((yy - SUN[1]) * 1.15) ** 2)
    glow = np.exp(-d / 260.0) * 0.55 + np.exp(-d / 70.0) * 0.6
    glow[HORIZON:] *= 0.35
    img += glow[..., None] * np.array([255, 205, 140], np.float32)
    sun = (d < 85) & (yy < HORIZON)
    img[sun] = np.array([255, 240, 200], np.float32)
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))


def ridge(width, base, amp, seed, octaves):
    rnd = random.Random(seed)
    prof = np.zeros(width, np.float32)
    for k in range(octaves):
        freq = (k + 1) * 2 * math.pi / width * rnd.choice([1, 2, 3])
        phase = rnd.random() * 6.28
        prof += np.sin(np.arange(width) * freq * (k + 1) + phase) * amp / (k + 1)
    return base - prof


def build_strip(width, top_y, amp, color, seed, trees=False):
    """Pas sylwetek nad horyzontem, zapętlany poziomo."""
    h = HORIZON - top_y + int(amp * 2) + 40
    img = Image.new("RGBA", (width, h), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    prof = ridge(width, h - 60, amp, seed, 5)
    pts = [(x, float(prof[x])) for x in range(0, width, 4)] + [(width, h), (0, h)]
    dr.polygon(pts, fill=color)
    if trees:
        rnd = random.Random(seed + 7)
        x = 0
        while x < width:
            th = rnd.randint(30, 90)
            tw = rnd.randint(14, 26)
            y = prof[min(int(x), width - 1)] + 6
            dr.polygon([(x - tw, y), (x, y - th), (x + tw, y)], fill=color)
            x += rnd.randint(12, 40)
    return img, h


# ---------------------------------------------------------------- kinematyka wioślarza

def stroke_state(p):
    """Zwraca (nogi, plecy, ręce, w_wodzie) w [0,1] dla fazy cyklu p."""
    if p < DRIVE:
        d = p / DRIVE
        legs, back, arms = smooth(0, 0.6, d), smooth(0.3, 0.85, d), smooth(0.6, 1.0, d)
    else:
        r = (p - DRIVE) / (1 - DRIVE)
        arms = 1 - smooth(0, 0.25, r)
        back = 1 - smooth(0.15, 0.45, r)
        legs = 1 - smooth(0.35, 1.0, r)
    if p < DRIVE:
        inwater = smooth(0.0, 0.04, p)
    elif p < DRIVE + 0.07:
        inwater = 1 - smooth(DRIVE, DRIVE + 0.07, p)
    elif p > 0.93:
        inwater = smooth(0.93, 1.0, p) * 0.6
    else:
        inwater = 0.0
    return legs, back, arms, inwater


def ik(a, b, l1, l2, bend):
    """Staw pośredni dwóch odcinków od a do b; bend=+1/-1 wybiera stronę zgięcia."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    d = max(min(math.hypot(dx, dy), l1 + l2 - 1e-3), 1e-3)
    ang = math.atan2(dy, dx)
    c = (l1 * l1 + d * d - l2 * l2) / (2 * l1 * d)
    off = math.acos(max(-1, min(1, c)))
    t = ang - bend * off
    return (a[0] + l1 * math.cos(t), a[1] + l1 * math.sin(t))


def rower_pose(sx, p):
    legs, back, arms, inwater = stroke_state(p)
    feet = (sx - 72, DECK - 8)
    hip = (sx + lerp(0, 78, legs), DECK - 22)
    knee = ik(hip, feet, 78, 74, -1)
    a = math.radians(lerp(-32, 22, back))
    torso = 102
    sh = (hip[0] + torso * math.sin(a), hip[1] - torso * math.cos(a))
    head = (sh[0] + 14 * math.sin(a) - 4, sh[1] - 28)
    ext = (sh[0] - 98, sh[1] + 26)
    pulled = (sh[0] + 6, sh[1] + 44)
    hand = (lerp(ext[0], pulled[0], arms), lerp(ext[1], pulled[1], arms) + (1 - inwater) * 6)
    elbow = ik(sh, hand, 54, 52, -1)
    return dict(feet=feet, hip=hip, knee=knee, sh=sh, head=head, hand=hand, elbow=elbow,
                inwater=inwater)


def oar_points(sx, pose, near):
    pivot = (sx - 12, DECK - 34)
    hx = pose["hand"][0]
    bx = pivot[0] - 1.5 * (hx - pivot[0])
    if near:
        by = lerp(WATERLINE - 40, WATERLINE + 92, pose["inwater"])
    else:
        by = lerp(WATERLINE - 95, WATERLINE - 14, pose["inwater"])
    return pose["hand"], pivot, (bx, by)


# ---------------------------------------------------------------- rysowanie łodzi

ROWER_COL = (24, 26, 48)
TOP_COL = (200, 48, 62)
HULL_COL = (236, 202, 70)
HULL_DARK = (120, 92, 40)
OAR_COL = (30, 32, 52)
BLADE_COL = (230, 60, 70)
STATIONS = [-300, -95, 110, 315]
LAYER_Y0 = 820          # górna krawędź warstwy łodzi w klatce
LAYER_H = 560


def P(pt, ox):
    return ((pt[0] + ox) * S, (pt[1] - LAYER_Y0) * S)


def line(dr, a, b, ox, w, col):
    dr.line([P(a, ox), P(b, ox)], fill=col, width=int(w * S))
    for q in (a, b):
        x, y = P(q, ox)
        r = w * S / 2
        dr.ellipse([x - r, y - r, x + r, y + r], fill=col)


def draw_oar(dr, sx, pose, ox, near):
    hand, pivot, blade = oar_points(sx, pose, near)
    col = OAR_COL if near else (60, 58, 86)
    line(dr, hand, blade, ox, 6, col)
    ang = math.atan2(blade[1] - hand[1], blade[0] - hand[0])
    bw, bl = 13, 46
    cx, cy = blade
    ca, sa = math.cos(ang), math.sin(ang)
    pts = [(cx - ca * bl * 0.2 - sa * bw, cy - sa * bl * 0.2 + ca * bw),
           (cx + ca * bl - sa * bw, cy + sa * bl + ca * bw),
           (cx + ca * bl + sa * bw, cy + sa * bl - ca * bw),
           (cx - ca * bl * 0.2 + sa * bw, cy - sa * bl * 0.2 - ca * bw)]
    dr.polygon([P(q, ox) for q in pts], fill=BLADE_COL if near else (170, 60, 80))


def draw_rower(dr, sx, pose, ox):
    line(dr, pose["feet"], pose["knee"], ox, 16, ROWER_COL)
    line(dr, pose["knee"], pose["hip"], ox, 20, ROWER_COL)
    line(dr, pose["hip"], pose["sh"], ox, 30, TOP_COL)
    line(dr, pose["sh"], pose["elbow"], ox, 13, ROWER_COL)
    line(dr, pose["elbow"], pose["hand"], ox, 12, ROWER_COL)
    hx, hy = P(pose["head"], ox)
    r = 19 * S
    dr.ellipse([hx - r, hy - r, hx + r, hy + r], fill=ROWER_COL)
    # czapka
    dr.chord([hx - r, hy - r, hx + r, hy + r * 0.6], 180, 360, fill=TOP_COL)
    seat = (pose["hip"][0], DECK - 8)
    dr.rectangle([P((seat[0] - 18, seat[1] - 4), ox), P((seat[0] + 18, seat[1] + 4), ox)], fill=(60, 60, 70))


def draw_hull(dr, ox):
    x0, x1 = -520, 520
    top = [(x0, DECK + 6)]
    for i in range(41):
        x = lerp(x0 + 30, x1 - 30, i / 40)
        top.append((x, DECK - 2 + 3 * math.sin(i / 40 * math.pi)))
    top.append((x1, DECK + 6))
    bottom = []
    for i in range(41):
        x = lerp(x1 - 20, x0 + 20, i / 40)
        bottom.append((x, WATERLINE + 6 + 4 * math.sin(i / 40 * math.pi)))
    dr.polygon([P(q, ox) for q in top + bottom], fill=HULL_COL)
    dr.line([P((x0 + 20, DECK + 3), ox), P((x1 - 20, DECK + 3), ox)], fill=HULL_DARK, width=3 * S)
    dr.line([P((x0 + 60, WATERLINE + 2), ox), P((x1 - 60, WATERLINE + 2), ox)], fill=(250, 230, 140), width=2 * S)
    for sx in STATIONS:
        dr.line([P((sx - 12, DECK - 34), ox), P((sx - 30, DECK + 2), ox)], fill=(70, 70, 80), width=4 * S)
        dr.line([P((sx - 12, DECK - 34), ox), P((sx + 8, DECK + 2), ox)], fill=(70, 70, 80), width=4 * S)
    # numer na dziobie
    fnt = font(FONT_B, 22 * S)
    dr.text(P((x1 - 120, DECK + 2), ox), "POL", font=fnt, fill=(40, 40, 70))


def render_boat(t, ox):
    layer = Image.new("RGBA", (W * S, LAYER_H * S), (0, 0, 0, 0))
    dr = ImageDraw.Draw(layer)
    p = ((t - T0) / STROKE_T) % 1.0
    poses = [rower_pose(sx, p) for sx in STATIONS]
    for i, (sx, pose) in enumerate(zip(STATIONS, poses)):
        if i % 2 == 1:
            draw_oar(dr, sx, pose, ox, near=False)
    draw_hull(dr, ox)
    for sx, pose in zip(STATIONS, poses):
        draw_rower(dr, sx, pose, ox)
    for i, (sx, pose) in enumerate(zip(STATIONS, poses)):
        if i % 2 == 0:
            draw_oar(dr, sx, pose, ox, near=True)
    return layer.resize((W, LAYER_H), Image.LANCZOS), p, poses


# ---------------------------------------------------------------- ruch / efekty

def boat_speed(t):
    p = ((t - T0) / STROKE_T) % 1.0
    surge = math.sin(min(p / (DRIVE + 0.12), 1.0) * math.pi)
    return 300 + 160 * surge - 60


class Effects:
    def __init__(self):
        self.puddles = []    # [x_world, y, wiek]
        self.drops = []      # [x, y, vx, vy, życie]
        self.rnd = random.Random(3)
        self.last_p = None

    def update(self, dt, p, poses, scroll, boat_ox):
        if self.last_p is not None:
            crossed_catch = self.last_p > 0.9 and p < 0.1
            crossed_finish = self.last_p < DRIVE + 0.02 <= p
            for i, (sx, pose) in enumerate(zip(STATIONS, poses)):
                if i % 2:
                    continue
                _, _, blade = oar_points(sx, pose, True)
                bx = blade[0] + boat_ox
                if crossed_catch or crossed_finish:
                    for _ in range(14 if crossed_catch else 9):
                        self.drops.append([bx + self.rnd.uniform(-25, 25), WATERLINE + 85,
                                           self.rnd.uniform(-160, 60), self.rnd.uniform(-420, -160), 0.0])
                if crossed_finish:
                    self.puddles.append([bx + scroll, WATERLINE + 100, 0.0])
        self.last_p = p
        for d in self.drops:
            d[0] += d[2] * dt
            d[1] += d[3] * dt
            d[3] += 900 * dt
            d[4] += dt
        self.drops = [d for d in self.drops if d[4] < 0.8 and d[1] < WATERLINE + 110]
        for pd in self.puddles:
            pd[2] += dt
        self.puddles = [pd for pd in self.puddles if pd[2] < 4.0]

    def draw(self, dr, scroll):
        for x, y, age in self.puddles:
            sx = x - scroll
            a = max(0, 1 - age / 4.0)
            for k, r in enumerate((26, 44, 62)):
                rr = r + age * 14
                col = (int(150 + 80 * a), int(130 + 70 * a), int(150 + 50 * a))
                dr.ellipse([sx - rr, y - rr * 0.22 + k * 3, sx + rr, y + rr * 0.22 + k * 3], outline=col, width=2)
        for x, y, *_ in self.drops:
            dr.ellipse([x - 4, y - 4, x + 4, y + 4], fill=(240, 230, 220))


def draw_water_detail(dr, scroll, t, rnd_seed):
    rnd = random.Random(rnd_seed)
    # odbicie słońca
    for i in range(60):
        y = HORIZON + 8 + i * 7 + (i * i) * 0.12
        if y > H:
            break
        w = (120 - i * 1.2) * (0.6 + 0.4 * math.sin(t * 3 + i * 1.7 + rnd.random()))
        if w <= 4:
            continue
        cx = SUN[0] + math.sin(t * 2 + i) * 6
        a = max(0.0, 1 - i / 60)
        col = mix((120, 80, 110), (255, 225, 170), a)
        dr.line([(cx - w, y), (cx + w, y)], fill=col, width=3)
    # linie fal z paralaksą (bliżej = szybciej)
    for row in range(26):
        depth = row / 25
        y = HORIZON + 20 + depth ** 1.6 * (H - HORIZON - 40)
        par = 0.2 + depth * 1.6
        spacing = 260 - depth * 120
        length = 30 + depth * 90
        off = (scroll * par + row * 97) % spacing
        col = mix((210, 150, 140), (70, 90, 150), depth)
        x = -off
        while x < W + spacing:
            jitter = math.sin(row * 13.1 + x * 0.01) * 20
            dr.line([(x + jitter, y), (x + jitter + length, y)], fill=col, width=2 + int(depth * 2))
            x += spacing


def draw_buoys(dr, scroll):
    spacing = 360
    for lane_y, size in ((HORIZON + 60, 7), (1440, 16)):
        par = 0.45 if size < 10 else 2.2
        off = (scroll * par) % spacing
        x = -off
        n = int((scroll * par) // spacing)
        while x < W + spacing:
            col = (230, 70, 60) if n % 2 else (245, 230, 210)
            dr.ellipse([x - size, lane_y - size, x + size, lane_y + size], fill=col)
            x += spacing
            n += 1


# ---------------------------------------------------------------- tekst

def text_center(img, txt, y, fnt, fill, alpha=1.0, spacing=0, shadow=True):
    if alpha <= 0:
        return
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    dr = ImageDraw.Draw(layer)
    widths = [dr.textlength(c, font=fnt) for c in txt]
    total = sum(widths) + spacing * (len(txt) - 1)
    x = (W - total) / 2
    a = int(255 * alpha)
    for c, w in zip(txt, widths):
        if shadow:
            dr.text((x + 4, y + 5), c, font=fnt, fill=(10, 10, 30, int(a * 0.55)))
        dr.text((x, y), c, font=fnt, fill=fill + (a,))
        x += w + spacing
    img.alpha_composite(layer)


def fade(t, a, b, f=0.35):
    if t < a or t > b:
        return 0.0
    return min(1.0, (t - a) / f, (b - t) / f)


PHASES = [(0.0, 0.10, "CHWYT"), (0.10, DRIVE, "NAPĘD"), (DRIVE, DRIVE + 0.14, "WYJŚCIE"), (DRIVE + 0.14, 1.0, "POWRÓT")]


def draw_overlay(img, t, p, dist, speed_ms):
    F_TITLE = font(FONT_B, 116)
    F_SUB = font(FONT_R, 54)
    F_PHASE = font(FONT_B, 120)
    F_SMALL = font(FONT_B, 40)
    F_HUD = font(FONT_B, 64)
    F_MID = font(FONT_B, 92)

    # 0–3 s: tytuł
    a = fade(t, 0.2, 3.2, 0.6)
    text_center(img, "WIOSŁOWANIE", 300 - (1 - a) * 30, F_TITLE, (255, 244, 225), a, spacing=3)
    text_center(img, "o świcie, w rytmie 30/min", 480, F_SUB, (255, 220, 190), fade(t, 0.8, 3.2, 0.6))

    # 3–8.5 s: fazy cyklu wiosłowania
    if 3.4 <= t <= 8.5:
        ga = fade(t, 3.4, 8.5, 0.3)
        for a0, a1, name in PHASES:
            if a0 <= p < a1:
                local = (p - a0) / (a1 - a0)
                pa = min(1.0, local * 6, (1 - local) * 6) * ga
                text_center(img, name, 330, F_PHASE, (255, 244, 225), pa, spacing=4)
        text_center(img, "TECHNIKA", 250, F_SMALL, (255, 200, 160), ga, spacing=10)

    # 8.5–12.6 s: "Nogi. Plecy. Ręce." + HUD
    words = [(8.6, "NOGI."), (9.4, "PLECY."), (10.2, "RĘCE.")]
    for i, (t_in, w) in enumerate(words):
        wa = fade(t, t_in, 12.4, 0.25)
        text_center(img, w, 260 + i * 110, F_MID, (255, 244, 225), wa, spacing=3)

    hud_a = fade(t, 3.4, 12.6, 0.4)
    if hud_a > 0:
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        dr = ImageDraw.Draw(layer)
        y0 = 1530
        dr.rounded_rectangle([60, y0, W - 60, y0 + 190], radius=36, fill=(12, 16, 40, int(150 * hud_a)))
        split = 500.0 / max(speed_ms, 0.1)
        mm, ss = divmod(split, 60)
        cols = [("TEMPO", "30"), ("SPLIT /500m", f"{int(mm)}:{ss:04.1f}"), ("DYSTANS", f"{int(dist)} m")]
        cw = (W - 120) / 3
        fl = font(FONT_R, 32)
        for i, (lab, val) in enumerate(cols):
            cx = 60 + cw * i + cw / 2
            lw = dr.textlength(lab, font=fl)
            vw = dr.textlength(val, font=F_HUD)
            dr.text((cx - lw / 2, y0 + 30), lab, font=fl, fill=(255, 200, 160, int(255 * hud_a)))
            dr.text((cx - vw / 2, y0 + 80), val, font=F_HUD, fill=(255, 248, 235, int(255 * hud_a)))
        img.alpha_composite(layer)

    # 12.6–16 s: zakończenie
    oa = fade(t, 12.7, 16.5, 0.5)
    text_center(img, "ZŁAP RYTM.", 300, font(FONT_B, 130), (255, 244, 225), oa, spacing=4)
    text_center(img, "Wsiadaj do łódki.", 470, F_SUB, (255, 220, 190), fade(t, 13.3, 16.5, 0.5))
    text_center(img, "#wioślarstwo  #rowing  #sunrise", 1640, F_SMALL, (255, 210, 180), fade(t, 13.8, 16.5, 0.5), shadow=False)


# ---------------------------------------------------------------- audio

SR = 44100


def env(n, attack, decay):
    t = np.arange(n) / SR
    return np.minimum(t / max(attack, 1e-4), 1.0) * np.exp(-t / decay)


def note_hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def build_audio(path):
    n = int(DUR * SR)
    out = np.zeros(n, np.float32)
    rng = np.random.default_rng(1)
    beat = STROKE_T / 4           # 120 BPM, 1 cykl = 1 takt

    def add(sig, t0, gain=1.0):
        i = int(t0 * SR)
        if i >= n or i + len(sig) <= 0:
            return
        j = min(n, i + len(sig))
        out[max(i, 0):j] += sig[max(0, -i):j - i] * gain

    # stopa
    kn = int(0.45 * SR)
    kt = np.arange(kn) / SR
    kick = np.sin(2 * np.pi * (45 * kt + 110 * (1 - np.exp(-kt * 30)) / 30)) * np.exp(-kt * 7)
    # hi-hat
    hn = int(0.06 * SR)
    hat = rng.standard_normal(hn).astype(np.float32)
    hat = np.diff(hat, prepend=0) * env(hn, 0.001, 0.015)
    # plusk (szum filtrowany) i szum napędu
    sn = int(0.5 * SR)
    splash = rng.standard_normal(sn).astype(np.float32)
    splash = np.convolve(splash, np.ones(6) / 6, mode="same") * env(sn, 0.005, 0.12)
    wn = int(DRIVE * STROKE_T * SR)
    whoosh = np.convolve(rng.standard_normal(wn), np.ones(40) / 40, mode="same").astype(np.float32)
    whoosh *= np.sin(np.linspace(0, np.pi, wn)) ** 2

    chords = [(57, 60, 64), (53, 57, 60), (48, 52, 55), (55, 59, 62)]   # Am F C G
    bass = [45, 41, 48, 43]

    k = 0
    t = T0
    while t < DUR:
        bar = k // 4
        in_beat = k % 4
        groove = t >= 2.9
        if groove and t < DUR - 1.0:
            add(kick, t, 0.9 if in_beat == 0 else 0.65)
            add(hat, t + beat / 2, 0.25)
        if in_beat == 0:
            add(splash, t + 0.02, 0.35)
            add(whoosh, t + 0.05, 0.18)
            # akord padu na cały takt
            ln = int(STROKE_T * SR)
            tt = np.arange(ln) / SR
            pad = np.zeros(ln, np.float32)
            for m in chords[bar % 4]:
                f = note_hz(m)
                pad += (np.sin(2 * np.pi * f * tt) + 0.4 * np.sin(2 * np.pi * f * 2.003 * tt)).astype(np.float32)
            pad *= np.minimum(tt / 0.4, 1.0) * np.minimum((STROKE_T - tt) / 0.4, 1.0)
            add(pad, t, 0.05)
            if groove:
                bl = int(STROKE_T * SR)
                bt = np.arange(bl) / SR
                f = note_hz(bass[bar % 4])
                b = np.tanh(2.5 * np.sin(2 * np.pi * f * bt)).astype(np.float32)
                pump = np.tile(env(int(beat * SR), 0.01, 0.25), 4)[:bl]
                add(b * pump, t, 0.16)
        t += beat
        k += 1
    # fade in/out
    fi = int(0.8 * SR)
    out[:fi] *= np.linspace(0, 1, fi)
    fo = int(1.5 * SR)
    out[-fo:] *= np.linspace(1, 0, fo)
    out /= max(1e-6, np.abs(out).max()) / 0.85
    pcm = (out * 32767).astype(np.int16)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(pcm.tobytes())


# ---------------------------------------------------------------- main

def main():
    wav = os.path.join(HERE, "_audio.wav")
    build_audio(wav)

    bg = build_background().convert("RGBA")
    far, far_h = build_strip(3000, HORIZON - 170, 40, (92, 62, 110, 255), 11)
    near, near_h = build_strip(3000, HORIZON - 120, 22, (44, 32, 66, 255), 23, trees=True)

    vignette = Image.new("L", (W, H), 0)
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.sqrt(((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H / 2) / (H * 0.7)) ** 2)
    vig = Image.fromarray((np.clip(d - 0.55, 0, 1) * 330).clip(0, 200).astype(np.uint8))
    vig_rgba = Image.new("RGBA", (W, H), (5, 5, 20, 0))
    vig_rgba.putalpha(vig)

    ff = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-i", wav,
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", OUT,
    ], stdin=subprocess.PIPE)

    fx = Effects()
    scroll = 0.0
    split_v = 5.3
    dt = 1.0 / FPS
    grain_rng = np.random.default_rng(5)
    for f in range(NFRAMES):
        t = f * dt
        v = boat_speed(t)
        scroll += v * dt
        dist = scroll / PX_PER_M
        split_v = lerp(split_v, v / PX_PER_M, 0.03)

        frame = bg.copy()
        for strip, sh, par in ((far, far_h, 0.04), (near, near_h, 0.12)):
            off = int(scroll * par) % strip.width
            y = HORIZON - sh + 40
            frame.alpha_composite(strip.crop((off, 0, min(off + W, strip.width), sh)), (0, y))
            if off + W > strip.width:
                frame.alpha_composite(strip.crop((0, 0, off + W - strip.width, sh)), (strip.width - off, y))
        # przycięcie sylwetek poniżej horyzontu
        frame.paste(bg.crop((0, HORIZON, W, HORIZON + 50)), (0, HORIZON))

        dr = ImageDraw.Draw(frame)
        draw_water_detail(dr, scroll, t, f // 3)
        draw_buoys(dr, scroll)

        boat_ox = W / 2 - 10 * math.sin(((t - T0) / STROKE_T % 1) * 2 * math.pi)
        boat, p, poses = render_boat(t, boat_ox)

        # odbicie łodzi w wodzie
        above = boat.crop((0, 0, W, WATERLINE - LAYER_Y0))
        refl = above.transpose(Image.FLIP_TOP_BOTTOM).filter(ImageFilter.GaussianBlur(3))
        r, g, b, a = refl.split()
        a = a.point(lambda x: int(x * 0.3))
        refl = Image.merge("RGBA", (r.point(lambda x: x // 2), g.point(lambda x: x // 2), b.point(lambda x: int(x * 0.7)), a))
        frame.alpha_composite(refl, (0, WATERLINE + 4))

        fx.update(dt, p, poses, scroll, boat_ox)
        fx.draw(dr, scroll)
        frame.alpha_composite(boat, (0, LAYER_Y0))

        frame.alpha_composite(vig_rgba)
        draw_overlay(frame, t, p, dist, split_v)

        arr = np.asarray(frame.convert("RGB"), dtype=np.int16)
        arr = arr + grain_rng.integers(-5, 6, size=(H, W, 1), dtype=np.int16)
        # wejście z czerni i wyjście do czerni
        k = min(1.0, t / 0.6, (DUR - t) / 0.8)
        arr = (np.clip(arr, 0, 255) * max(k, 0.0)).astype(np.uint8)
        ff.stdin.write(arr.tobytes())
        if f % 60 == 0:
            print(f"klatka {f}/{NFRAMES}", flush=True)

    ff.stdin.close()
    ff.wait()
    os.remove(wav)
    print("Gotowe:", OUT)


if __name__ == "__main__":
    main()
