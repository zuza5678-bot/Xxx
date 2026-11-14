"""Rolka 9:16 w stylu stickman: "SKORPION". Paleta: granat, czerń, szary.

Uruchom: python3 muzyka.py && python3 rolka.py  ->  skorpion_rolka.mp4
"""
import math
import random
import subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
SS = 2  # supersampling (antyaliasing)
FPS = 30
DUR = 27.0
GROUND = 1340

# Paleta
BLACK = (5, 7, 12)
NAVY_D = (10, 18, 42)
NAVY = (22, 38, 88)
NAVY_L = (44, 66, 132)
GRAY_D = (52, 56, 66)
GRAY = (122, 128, 140)
GRAY_L = (200, 204, 212)
WHITE = (236, 238, 242)

FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_R = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
fonts = {}


def font(size, bold=True):
    key = (size, bold)
    if key not in fonts:
        fonts[key] = ImageFont.truetype(FONT_B if bold else FONT_R, int(size * SS))
    return fonts[key]


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def lerp(a, b, t):
    return a + (b - a) * t


def mix(c1, c2, t):
    return tuple(int(lerp(a, b, t)) for a, b in zip(c1, c2))


# ---------------------------------------------------------------- tło
def make_sky():
    img = Image.new("RGB", (W * SS, H * SS))
    arr = np.zeros((H * SS, W * SS, 3), np.uint8)
    for y in range(H * SS):
        t = clamp(y / (GROUND * SS))
        c = mix(BLACK, NAVY_D, t ** 1.6)
        arr[y, :] = c
    img = Image.fromarray(arr)
    return img


SKY = make_sky()
random.seed(7)
STARS = [(random.uniform(0, W * 3), random.uniform(40, GROUND - 350), random.uniform(1.2, 3.2),
          random.uniform(0, 6.28)) for _ in range(170)]


def dune_y(x, layer):
    if layer == 0:
        return GROUND - 260 + 60 * math.sin(x / 420) + 35 * math.sin(x / 170 + 1.3)
    if layer == 1:
        return GROUND - 140 + 45 * math.sin(x / 300 + 2) + 20 * math.sin(x / 110)
    return GROUND


class Canvas:
    def __init__(self, cam_x=0.0, shake=(0, 0), zoom=1.0):
        self.img = SKY.copy()
        self.d = ImageDraw.Draw(self.img)
        self.cx = cam_x
        self.sx, self.sy = shake
        self.zoom = zoom

    # przelicz współrzędne świata -> piksele (z supersamplingiem)
    def p(self, x, y, par=1.0):
        X = (x - self.cx * par - W / 2) * self.zoom + W / 2 + self.sx
        Y = (y - GROUND) * self.zoom + GROUND + self.sy
        return X * SS, Y * SS

    def line(self, pts, col, w, par=1.0):
        pp = [self.p(x, y, par) for x, y in pts]
        self.d.line(pp, fill=col, width=max(1, int(w * SS * self.zoom)), joint="curve")
        r = w * SS * self.zoom / 2
        for X, Y in (pp[0], pp[-1]):
            self.d.ellipse([X - r, Y - r, X + r, Y + r], fill=col)

    def circle(self, x, y, r, fill=None, outline=None, w=0, par=1.0):
        X, Y = self.p(x, y, par)
        R = r * SS * self.zoom
        self.d.ellipse([X - R, Y - R, X + R, Y + R], fill=fill, outline=outline,
                       width=int(w * SS * self.zoom) if w else 0)

    def ellipse(self, x, y, rx, ry, fill=None, outline=None, w=0):
        X, Y = self.p(x, y)
        self.d.ellipse([X - rx * SS * self.zoom, Y - ry * SS * self.zoom,
                        X + rx * SS * self.zoom, Y + ry * SS * self.zoom],
                       fill=fill, outline=outline, width=int(w * SS * self.zoom) if w else 0)

    def poly(self, pts, fill, par=1.0):
        self.d.polygon([self.p(x, y, par) for x, y in pts], fill=fill)

    def text(self, s, x, y, size, col, bold=True, anchor="mm", stroke=0, stroke_col=BLACK):
        self.d.text((x * SS, y * SS), s, font=font(size, bold), fill=col, anchor=anchor,
                    stroke_width=int(stroke * SS), stroke_fill=stroke_col)

    def rect(self, x0, y0, x1, y1, fill, r=0):
        self.d.rounded_rectangle([x0 * SS, y0 * SS, x1 * SS, y1 * SS], radius=r * SS, fill=fill)

    def final(self):
        return self.img.resize((W, H), Image.LANCZOS)


def draw_background(c, t):
    # gwiazdy
    for sx, sy, r, ph in STARS:
        x = (sx - c.cx * 0.1) % (W + 40) - 20
        tw = 0.55 + 0.45 * math.sin(t * 2.2 + ph)
        col = mix(NAVY_D, GRAY_L, tw * 0.9)
        R = r * SS
        c.d.ellipse([x * SS - R, sy * SS - R, x * SS + R, sy * SS + R], fill=col)
    # księżyc (sierp)
    mx, my = 790 - c.cx * 0.05, 330
    c.d.ellipse([(mx - 95) * SS, (my - 95) * SS, (mx + 95) * SS, (my + 95) * SS], fill=GRAY_L)
    for k in range(3):
        c.d.ellipse([(mx - 95 - 8 * k) * SS, (my - 120 + 3 * k) * SS,
                     (mx + 60 - 8 * k) * SS, (my + 60 + 3 * k) * SS],
                    fill=mix(BLACK, NAVY_D, 0.25)) if k == 0 else None
    # wydmy (paralaksa)
    for layer, (par, col) in enumerate([(0.3, (16, 26, 58)), (0.6, (24, 38, 80))]):
        pts = []
        for i in range(0, W + 41, 40):
            wx = i + c.cx * par
            pts.append((i, dune_y(wx, layer)))
        pts += [(W + 40, H), (-40, H)]
        c.d.polygon([(x * SS, ((y - GROUND) * c.zoom + GROUND + c.sy) * SS) for x, y in pts],
                    fill=col)
    # ziemia
    gy = (GROUND + c.sy) * SS
    c.d.rectangle([0, gy, W * SS, H * SS], fill=(30, 33, 42))
    c.d.line([(0, gy), (W * SS, gy)], fill=GRAY, width=3 * SS)
    # kamyczki na ziemi
    rnd = random.Random(3)
    for i in range(60):
        wx = rnd.uniform(-600, 4200)
        wy = GROUND + rnd.uniform(20, 160)
        X = (wx - c.cx - W / 2) * c.zoom + W / 2 + c.sx
        if -20 < X < W + 20:
            r = rnd.uniform(3, 9)
            c.d.ellipse([(X - r) * SS, (wy - r * 0.5 + c.sy) * SS, (X + r) * SS, (wy + r * 0.5 + c.sy) * SS],
                        fill=GRAY_D)


def cactus(c, x):
    col = (40, 46, 60)
    c.line([(x, GROUND), (x, GROUND - 330)], col, 46)
    c.line([(x - 18, GROUND - 160), (x - 85, GROUND - 160), (x - 85, GROUND - 250)], col, 30)
    c.line([(x + 18, GROUND - 200), (x + 75, GROUND - 200), (x + 75, GROUND - 290)], col, 30)


def rock(c, x):
    c.poly([(x - 150, GROUND), (x - 120, GROUND - 120), (x - 40, GROUND - 190), (x + 70, GROUND - 175),
            (x + 140, GROUND - 90), (x + 160, GROUND)], (44, 48, 60))
    c.line([(x - 40, GROUND - 190), (x + 70, GROUND - 175)], GRAY, 4)


# ---------------------------------------------------------------- stickman
def stickman(c, x, gy, phase=0.0, mode="stand", face=1, jump=0.0, lean=0.0, t=0.0):
    col = GRAY_L
    lw = 13
    thigh, shin = 70, 68
    upper, fore = 55, 52
    bob = 0
    if mode in ("walk", "run"):
        bob = -abs(math.sin(phase)) * (8 if mode == "walk" else 16)
    hip = (x, gy - thigh - shin - jump + bob + 4)
    if mode == "sit":
        hip = (x, gy - jump)
    lean_a = {"run": 0.35, "walk": 0.06}.get(mode, 0.0) + lean
    torso = 115
    sh = (hip[0] + math.sin(lean_a) * torso * face, hip[1] - math.cos(lean_a) * torso)
    head_r = 34
    head = (sh[0] + math.sin(lean_a) * (head_r + 14) * face, sh[1] - math.cos(lean_a) * (head_r + 14))

    def pt(o, a, ln):  # a: 0 = w dół, + = do przodu
        return (o[0] + math.sin(a) * ln * face, o[1] + math.cos(a) * ln)

    # nogi
    for k in (0, 1):
        p = phase + k * math.pi
        if mode == "walk":
            a1 = 0.45 * math.sin(p)
            a2 = a1 - 0.6 * max(0, -math.cos(p))
        elif mode == "run":
            a1 = 0.85 * math.sin(p)
            a2 = a1 - 1.3 * max(0, -math.cos(p)) - 0.2
        elif mode == "scared":
            a1 = (-0.25 if k else 0.3)
            a2 = a1 - 0.2
        elif mode == "sit":
            a1, a2 = 1.45, 0.25 + (0.2 * math.sin(t * 6 + k * 2))
        else:
            a1 = 0.12 if k else -0.12
            a2 = a1
        knee = pt(hip, a1, thigh)
        foot = pt(knee, a2, shin)
        c.line([hip, knee, foot], col, lw)
    # tułów
    c.line([hip, sh], col, lw)
    # ręce
    for k in (0, 1):
        p = phase + k * math.pi
        if mode == "walk":
            a1 = -0.45 * math.sin(p)
            a2 = a1 + 0.35
        elif mode == "run":
            a1 = -1.0 * math.sin(p) + 0.2
            a2 = a1 + 1.6
        elif mode == "scared":
            a1 = 2.5 + 0.15 * math.sin(t * 30 + k) if k == 0 else -2.4 + 0.15 * math.sin(t * 30)
            a2 = a1 + (0.4 if k == 0 else -0.4)
        elif mode == "sit":
            a1 = 2.6 if k == 0 else 0.3
            a2 = a1 + (0.5 * math.sin(t * 8) if k == 0 else 0.6)
        else:
            a1 = 0.18 if k else -0.18
            a2 = a1
        el = pt(sh, a1, upper)
        hd = pt(el, a2, fore)
        c.line([sh, el, hd], col, lw)
    # głowa
    c.circle(head[0], head[1], head_r, fill=BLACK, outline=col, w=lw)
    # oczy
    ex = head[0] + 12 * face
    if mode == "scared":
        c.circle(ex - 4 * face, head[1] - 6, 8, fill=WHITE)
        c.circle(ex + 10 * face, head[1] - 6, 8, fill=WHITE)
        c.circle(ex - 4 * face, head[1] - 6, 3, fill=BLACK)
        c.circle(ex + 10 * face, head[1] - 6, 3, fill=BLACK)
        c.circle(ex + 3 * face, head[1] + 14, 7, fill=BLACK, outline=col, w=3)
    else:
        c.circle(ex, head[1] - 5, 4.5, fill=col)
        c.circle(ex + 13 * face, head[1] - 5, 4.5, fill=col)
    return head


# ---------------------------------------------------------------- skorpion
def scorpion(c, x, gy, face=-1, tail=1.0, claw=0.5, phase=0.0, emerge=1.0, sting=0.0, scale=1.0):
    """face: -1 patrzy w lewo, +1 w prawo. emerge 0..1 = wychodzenie z piasku."""
    s = scale
    out = GRAY_L
    fill = NAVY
    lw = 6
    sink = (1 - emerge) * 200 * s
    by = gy - 52 * s + sink

    def P(lx, ly):  # lokalne -> świat (lx do przodu)
        return (x + lx * face * s, by + ly * s)

    # nogi (4 pary, tylne ciemniejsze)
    for side, colr in ((1, GRAY), (0, out)):
        for i in range(4):
            lx = 45 - i * 32 + side * 10
            p = phase + i * 1.3 + side * math.pi
            lift = max(0, math.sin(p)) * 14
            step = math.cos(p) * 12
            hip = P(lx, 8)
            knee = P(lx + 18 + (i < 2) * 10, -28 - lift * 0.5)
            foot = P(lx + 36 + (i < 2) * 18 - (i >= 2) * 30 + step, 52 - lift)
            if foot[1] > gy:
                foot = (foot[0], gy)
            c.line([hip, knee, foot], colr, 5 * s)

    # ogon: od tyłu, zakręca do góry i nad grzbiet
    base = P(-92, -4)
    pts = [base]
    a = math.pi  # w lewo (w lokalnych: do tyłu)
    seg = [34, 32, 30, 28, 26, 24]
    cur = (-92.0, -4.0)
    wig = math.sin(phase * 0.7) * 0.06
    for k, ln in enumerate(seg):
        a += (0.18 + 0.32 * tail) + wig + sting * (0.12 if k > 2 else -0.05)
        cur = (cur[0] + math.cos(a) * ln, cur[1] + math.sin(a) * ln)
        pts.append(P(*cur))
    for k, (px, py) in enumerate(pts):
        r = (17 - k * 1.6) * s
        c.circle(px, py, r / s * s, fill=fill, outline=out, w=4)
    # żądło
    tip_dir = a + 0.6
    tl = 30
    tip = (cur[0] + math.cos(tip_dir) * tl, cur[1] + math.sin(tip_dir) * tl)
    side_a = tip_dir + 1.5
    b1 = (cur[0] + math.cos(side_a) * 9, cur[1] + math.sin(side_a) * 9)
    b2 = (cur[0] - math.cos(side_a) * 9, cur[1] - math.sin(side_a) * 9)
    c.poly([P(*b1), P(*tip), P(*b2)], GRAY_L)

    # ciało: odwłok + głowotułów
    for k, (lx, rx, ry) in enumerate([(-75, 26, 24), (-50, 30, 27), (-22, 33, 29), (8, 34, 30), (40, 34, 28)]):
        px, py = P(lx, 0)
        c.ellipse(px, py, rx * s, ry * s, fill=fill, outline=out, w=4)
    # pręgi
    for lx in (-62, -36, -8):
        c.line([P(lx, -26), P(lx, 22)], NAVY_L, 3)

    # szczypce
    for side, colr in ((1, GRAY), (0, out)):
        sh = P(60, 6 - side * 4)
        el = P(100 + side * 8, -26 - side * 6)
        wr = P(138 + side * 10, -4 - side * 8)
        c.line([sh, el, wr], colr, 9 * s)
        # kleszcze
        op = 0.25 + claw * 0.55
        jaw_c = (138 + side * 10, -4 - side * 8)
        c.ellipse(*P(jaw_c[0] + 16, jaw_c[1]), 20 * s, 14 * s, fill=fill, outline=colr, w=4)
        upj = [P(jaw_c[0] + 28, jaw_c[1] - 4),
               P(jaw_c[0] + 28 + math.cos(-op) * 34, jaw_c[1] - 4 + math.sin(-op) * 34)]
        loj = [P(jaw_c[0] + 28, jaw_c[1] + 6),
               P(jaw_c[0] + 28 + math.cos(op) * 30, jaw_c[1] + 6 + math.sin(op) * 30)]
        c.line(upj, colr, 7 * s)
        c.line(loj, colr, 7 * s)
    # oczy
    c.circle(*P(58, -18), 5 * s, fill=WHITE)
    c.circle(*P(48, -20), 4 * s, fill=WHITE)

    # przykrywka z piasku przy wychodzeniu
    if emerge < 1:
        c.d.rectangle([0, (GROUND + c.sy) * SS, W * SS, H * SS], fill=(30, 33, 42))
        c.d.line([(0, (GROUND + c.sy) * SS), (W * SS, (GROUND + c.sy) * SS)], fill=GRAY, width=3 * SS)


def sand_mound(c, x, t, amp):
    if amp <= 0:
        return
    h = 30 + 40 * amp
    wob = math.sin(t * 40) * 6 * amp
    pts = []
    for i in range(21):
        u = i / 20
        xx = x - 120 + 240 * u
        pts.append((xx + wob, GROUND - h * math.sin(math.pi * u) ** 1.5))
    c.poly(pts + [(x + 120, GROUND + 2), (x - 120, GROUND + 2)], (46, 50, 62))
    c.line(pts, GRAY, 4)
    rnd = random.Random(int(t * 30))
    for _ in range(int(14 * amp)):
        px = x + rnd.uniform(-110, 110)
        py = GROUND - h - rnd.uniform(0, 90 * amp)
        c.circle(px, py, rnd.uniform(2, 6), fill=GRAY)


# ---------------------------------------------------------------- napisy
def caption(c, s, t, t0, t1, y=1620, size=60, col=WHITE, box=NAVY):
    if not (t0 <= t < t1):
        return
    a = ease((t - t0) / 0.25)
    b = ease((t1 - t) / 0.2)
    k = min(a, b)
    yy = y + (1 - a) * 40
    f = font(size)
    lines = s.split("\n")
    widths = [c.d.textlength(ln, font=f) / SS for ln in lines]
    wmax = max(widths)
    lh = size * 1.25
    hbox = lh * len(lines) + 40
    bc = mix((30, 33, 42), box, k)
    tc = mix((30, 33, 42), col, k)
    c.rect(W / 2 - wmax / 2 - 40, yy - hbox / 2, W / 2 + wmax / 2 + 40, yy + hbox / 2, bc, r=26)
    c.rect(W / 2 - wmax / 2 - 40, yy - hbox / 2, W / 2 - wmax / 2 - 28, yy + hbox / 2, mix(bc, GRAY_L, k), r=6)
    for i, ln in enumerate(lines):
        c.text(ln, W / 2, yy - hbox / 2 + 20 + lh * (i + 0.5), size, tc)


def top_label(c, s, t, t0, t1, y=170, size=44):
    if not (t0 <= t < t1):
        return
    k = min(ease((t - t0) / 0.3), ease((t1 - t) / 0.3))
    c.text(s, W / 2, y, size, mix(NAVY_D, GRAY, k))


# ---------------------------------------------------------------- scenariusz
def frame(t):
    shake = (0, 0)
    cam = 0.0
    zoom = 1.0

    # kamera: pościg -> panorama w prawo
    if t >= 16.0:
        cam = ease((t - 16.0) / 5.0) * 900
    if 10.0 <= t < 11.2:
        k = (11.2 - t) / 1.2
        shake = (math.sin(t * 90) * 22 * k, math.cos(t * 77) * 16 * k)
    if 10.0 <= t < 13.0:
        zoom = 1.0 + 0.12 * ease((t - 10.0) / 0.4) * (1 - ease((t - 12.4) / 0.6))
    c = Canvas(cam, shake, zoom)
    draw_background(c, t)

    cactus(c, 140)
    rock(c, 1700)

    SC_X = 760  # pozycja skorpiona
    SC = 1.55
    # ---------------- stickman
    if t < 7.0:
        sx = lerp(-120, 360, ease(t / 7.0) * 0.4 + clamp(t / 7.0) * 0.6)
        stickman(c, sx, GROUND, phase=t * 6.0, mode="walk", face=1)
    elif t < 10.0:
        # zatrzymuje się, rozgląda
        look = 1 if (t < 8.3 or t > 9.3) else -1
        stickman(c, 360, GROUND, mode="stand", face=look, t=t)
        if 8.6 < t < 10:
            c.text("?", 360 + 10, GROUND - 400, 90, GRAY_L)
    elif t < 16.0:
        tt = t - 13.0
        jump = 0.0
        if 13.0 <= t < 13.6:
            jump = math.sin((t - 13.0) / 0.6 * math.pi) * 170
        mode = "scared" if t >= 10.3 else "stand"
        sx = 360 - ease((t - 13.6) / 2.0) * 60 if t > 13.6 else 360
        head = stickman(c, sx, GROUND, mode=mode, face=1, jump=jump, t=t)
        if t >= 10.3:
            c.text("!", head[0] * 1 - c.cx, head[1] - 95, 110 + 10 * math.sin(t * 20), WHITE, stroke=3,
                   stroke_col=NAVY)
    elif t < 21.0:
        # ucieka w prawo
        if t < 16.9:
            u = (t - 16.0) / 0.9
            sx = lerp(300, 1050, u)
            stickman(c, sx, GROUND, phase=t * 15, mode="run", face=1,
                     jump=math.sin(u * math.pi) * 420)
        else:
            u = (t - 16.9) / 4.1
            sx = lerp(1050, 1650, u)
            stickman(c, sx, GROUND, phase=t * 15, mode="run", face=1)
        # linie prędkości
        for i in range(5):
            yy = GROUND - 80 - i * 45
            ox = (t * 1300 + i * 170) % 260
            c.line([(sx - 120 - ox, yy), (sx - 200 - ox, yy)], GRAY, 5)
    elif t < 24.5:
        # siedzi na skale
        if t < 21.6:
            u = (t - 21.0) / 0.6
            jump = math.sin(u * math.pi) * 120 + u * 190
            stickman(c, lerp(1650, 1720, u), GROUND, mode="run", phase=t * 15, face=1, jump=jump)
        else:
            stickman(c, 1720, GROUND - 190, mode="sit", face=-1, t=t)

    # ---------------- skorpion
    if 7.0 <= t < 10.0:
        amp = ease((t - 7.0) / 2.5)
        sand_mound(c, SC_X, t, amp)
    elif 10.0 <= t < 16.0:
        em = ease((t - 10.0) / 0.5)
        tail = ease((t - 10.2) / 0.8)
        claw = 0.5 + 0.5 * math.sin(t * 9)
        st = max(0, math.sin((t - 13.0) * 10)) if 13 < t < 14.2 else 0
        x = SC_X - ease((t - 14.0) / 2.0) * 120
        scorpion(c, x, GROUND, face=-1, tail=tail, claw=claw, phase=t * 8 if t > 14 else 0,
                 emerge=em, sting=st, scale=SC)
        if t < 10.6:
            sand_mound(c, SC_X, t, 1 - (t - 10.0) / 0.6)
    elif 16.0 <= t < 21.0:
        # goni stickmana
        face = -1 if t < 16.7 else 1
        u = clamp((t - 16.7) / 4.3)
        x = lerp(640, 1150, u)
        scorpion(c, x, GROUND, face=face, tail=1.0, claw=0.5 + 0.5 * math.sin(t * 14),
                 phase=t * 22, scale=SC)
    elif 21.0 <= t < 24.5:
        x = 1150 + ease((t - 21.0) / 0.8) * 60
        claw = 0.5 + 0.5 * math.sin(t * 16)
        st = 0.6 + 0.4 * math.sin(t * 7)
        scorpion(c, x, GROUND, face=1, tail=1.0, claw=claw, phase=t * 6 if t < 21.8 else 0,
                 sting=st, scale=SC)

    # ---------------- napisy
    if t < 3.2:
        k = min(ease(t / 0.6), ease((3.2 - t) / 0.4))
        c.text("SKORPION", W / 2, 700, 150, mix(NAVY_D, WHITE, k), stroke=6, stroke_col=mix(NAVY_D, NAVY, k))
        c.text("historia stickmana", W / 2, 830, 46, mix(NAVY_D, GRAY, k), bold=False)
    top_label(c, "rozdział 1: pustynia", t, 0.4, 7.0)
    caption(c, "Noc. Pustynia. Cisza...", t, 0.6, 3.6)
    caption(c, "Stickman wraca do domu.", t, 3.7, 7.0)
    caption(c, "Nagle... coś drgnęło\nw piasku.", t, 7.1, 10.0)
    if 10.0 <= t < 12.6:
        k = ease((t - 10.0) / 0.15)
        sz = 135 * (1.4 - 0.4 * k)
        c.text("SKORPION!", W / 2 + shake[0] * 0.5, 560, sz, WHITE, stroke=8, stroke_col=NAVY)
    caption(c, "Ośmionóg z żądłem.\nI wcale nie jest przyjazny.", t, 10.6, 13.0, size=52)
    caption(c, "Ups.", t, 13.1, 16.0, size=80)
    caption(c, "W NOGI!!!", t, 16.1, 21.0, size=90)
    caption(c, "Bezpieczny...\nchyba.", t, 21.3, 24.5)

    # zakończenie
    if t >= 24.3:
        k = ease((t - 24.3) / 0.7)
        ov = Image.new("RGB", c.img.size, BLACK)
        c.img = Image.blend(c.img, ov, 0.85 * k)
        c.d = ImageDraw.Draw(c.img)
        c.text("Uważaj, gdzie", W / 2, 820, 80, mix(BLACK, WHITE, k))
        c.text("stawiasz kroki.", W / 2, 920, 80, mix(BLACK, WHITE, k))
        c.rect(W / 2 - 160, 1010, W / 2 + 160, 1016, mix(BLACK, NAVY_L, k))
        c.text("Skorpion 1 : 0 Stickman", W / 2, 1090, 46, mix(BLACK, GRAY, k), bold=False)

    # winieta
    return c.final()


def vignette():
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.sqrt(((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H / 2) / (H * 0.7)) ** 2)
    return np.clip(1.05 - 0.55 * d ** 2, 0.45, 1.0)[..., None].astype(np.float32)


def main():
    import sys
    vig = vignette()
    if len(sys.argv) > 1:  # podgląd pojedynczych klatek
        for ts in sys.argv[1:]:
            im = frame(float(ts))
            arr = (np.asarray(im, np.float32) * vig).astype(np.uint8)
            Image.fromarray(arr).save(f"podglad_{ts}.png")
        return
    n = int(DUR * FPS)
    ff = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-i", "muzyka.wav",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart",
        "skorpion_rolka.mp4"], stdin=subprocess.PIPE)
    for i in range(n):
        im = frame(i / FPS)
        arr = (np.asarray(im, np.float32) * vig).astype(np.uint8)
        ff.stdin.write(arr.tobytes())
        if i % 60 == 0:
            print(f"{i}/{n}", flush=True)
    ff.stdin.close()
    ff.wait()
    print("skorpion_rolka.mp4 gotowa")


if __name__ == "__main__":
    main()
