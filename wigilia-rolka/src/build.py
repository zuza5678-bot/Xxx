"""Build the Wigilia reel: voice track + music + animated 1080x1920 frames -> MP4."""
import json, math, os, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
W, H, FPS, SR = 1080, 1920, 30, 44100
FD = "/usr/share/fonts/opentype/inter/"
def F(name, size): return ImageFont.truetype(FD + name, size)

GOLD = (243, 201, 105)
CREAM = (255, 246, 228)
RED = (226, 72, 72)

lines = [l.strip() for l in open("lines.txt", encoding="utf-8") if l.strip()]

# ---------------- timeline ----------------
def read_wav(p):
    with wave.open(p) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    n2 = int(len(x) * SR / sr)
    return np.interp(np.linspace(0, len(x) - 1, n2), np.arange(len(x)), x)

clips = [read_wav(f"v{i+1}.wav") for i in range(len(lines))]
extra_gap = {4: 0.55, 7: 0.9, 9: 0.75}  # index of line -> extra pause before it
t = 0.9
starts, durs = [], []
for i, c in enumerate(clips):
    t += extra_gap.get(i, 0)
    starts.append(t)
    durs.append(len(c) / SR)
    t += len(c) / SR + 0.38
TOTAL = starts[-1] + durs[-1] + 2.8
NF = int(TOTAL * FPS)

voice = np.zeros(int(TOTAL * SR) + SR)
for s, c in zip(starts, clips):
    i = int(s * SR); voice[i:i + len(c)] += c
voice /= np.max(np.abs(voice)) + 1e-9
voice *= 0.95
with wave.open("voice.wav", "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((voice * 32767).astype(np.int16).tobytes())

quiet0, quiet1 = starts[7] - 0.5, starts[9] - 0.1
subprocess.run([sys.executable, "music.py", f"{TOTAL:.3f}", f"{quiet0:.3f}", f"{quiet1:.3f}", "music.wav"], check=True)
json.dump({"starts": starts, "durs": durs, "total": TOTAL}, open("timeline.json", "w"), indent=1)

# ---------------- helpers ----------------
def ease_out(x): x = min(max(x, 0), 1); return 1 - (1 - x) ** 3
def ease_back(x):
    x = min(max(x, 0), 1); c = 1.7
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2
def clamp(x, a=0, b=1): return min(max(x, a), b)

def text_img(txt, font, fill, stroke=0, stroke_fill=(0, 0, 0), spacing=0, align="center", tracking=0):
    d = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    if tracking:
        txt = txt  # tracking handled via spaced string
    bb = [int(math.ceil(v)) for v in d.multiline_textbbox((0, 0), txt, font=font, stroke_width=stroke, spacing=spacing, align=align)]
    im = Image.new("RGBA", (bb[2] - bb[0] + 8, bb[3] - bb[1] + 8), (0, 0, 0, 0))
    ImageDraw.Draw(im).multiline_text((4 - bb[0], 4 - bb[1]), txt, font=font, fill=fill,
                                      stroke_width=stroke, stroke_fill=stroke_fill, spacing=spacing, align=align)
    return im

_cache = {}
def cached_text(key, *a, **k):
    if key not in _cache: _cache[key] = text_img(*a, **k)
    return _cache[key]

def paste(base, im, cx, cy, alpha=1.0, scale=1.0, glow=None):
    if alpha <= 0.01: return
    if abs(scale - 1) > 0.01:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.LANCZOS)
    if glow:
        pad = glow[1] * 3
        big = Image.new("RGBA", (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0)); big.alpha_composite(im, (pad, pad))
        g = big.filter(ImageFilter.GaussianBlur(glow[1]))
        col = Image.new("RGBA", g.size, glow[0] + (0,)); col.putalpha(g.getchannel("A").point(lambda v: int(v * glow[2])))
        _alpha_paste(base, col, cx, cy, alpha)
    _alpha_paste(base, im, cx, cy, alpha)

def _alpha_paste(base, im, cx, cy, alpha):
    if alpha < 0.999:
        a = im.getchannel("A").point(lambda v: int(v * alpha)); im = im.copy(); im.putalpha(a)
    base.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))

def star_poly(cx, cy, r, inner=0.42, rot=-90):
    pts = []
    for k in range(10):
        rr = r if k % 2 == 0 else r * inner
        a = math.radians(rot + k * 36)
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return pts

# ---------------- static layers ----------------
def gradient(top, bot):
    y = np.linspace(0, 1, H)[:, None, None]
    arr = (np.array(top)[None, None] * (1 - y) + np.array(bot)[None, None] * y)
    return np.repeat(arr, W, 1)
BG_A = gradient((8, 12, 34), (10, 38, 32))
BG_B = gradient((22, 8, 20), (8, 14, 36))

rng = np.random.default_rng(3)
BW, BH = int(W * 1.3), int(H * 1.3)
bokeh = Image.new("RGBA", (BW, BH), (0, 0, 0, 0))
bd = ImageDraw.Draw(bokeh)
for _ in range(38):
    x, y, r = rng.uniform(0, BW), rng.uniform(0, BH), rng.uniform(25, 110)
    col = [GOLD, (255, 170, 90), RED, (120, 220, 170), CREAM][rng.integers(0, 5)]
    bd.ellipse((x - r, y - r, x + r, y + r), fill=col + (int(rng.uniform(25, 70)),))
bokeh = bokeh.filter(ImageFilter.GaussianBlur(18))

vignette = Image.new("L", (W, H), 0)
yy, xx = np.mgrid[0:H, 0:W]
d = np.sqrt(((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H / 2) / (H * 0.62)) ** 2)
vignette = Image.fromarray((np.clip(d - 0.55, 0, 1) * 330).clip(0, 200).astype(np.uint8))
VIG = Image.new("RGBA", (W, H), (0, 0, 0, 0)); VIG.putalpha(vignette)

NSNOW = 170
snow = np.stack([rng.uniform(0, W, NSNOW), rng.uniform(-H, H, NSNOW), rng.uniform(1.5, 6.5, NSNOW),
                 rng.uniform(0, 6.28, NSNOW)], 1)

# fonts
f_huge = F("InterDisplay-Black.otf", 300)
f_big = F("InterDisplay-Black.otf", 150)
f_h = F("InterDisplay-ExtraBold.otf", 104)
f_mid = F("InterDisplay-Bold.otf", 64)
f_kick = F("Inter-SemiBold.otf", 34)
f_cap = F("Inter-ExtraBold.otf", 58)
f_chip = F("InterDisplay-Bold.otf", 54)
f_small = F("Inter-SemiBold.otf", 40)

def kicker(img, txt, y, a):
    im = cached_text("k" + txt, " ".join(txt), f_kick, GOLD)
    paste(img, im, W / 2, y, a)
    dr = ImageDraw.Draw(img)
    w = im.width / 2 + 30
    al = int(200 * a)
    dr.line((W / 2 - w - 70, y, W / 2 - w, y), fill=GOLD + (al,), width=3)
    dr.line((W / 2 + w, y, W / 2 + w + 70, y), fill=GOLD + (al,), width=3)

# word timings for captions (proportional to characters)
word_times = []
for s, du, l in zip(starts, durs, lines):
    ws = l.split()
    tot = sum(len(w) + 1.5 for w in ws)
    acc, wt = 0, []
    for w in ws:
        a0 = s + 0.12 + (du - 0.25) * acc / tot
        acc += len(w) + 1.5
        wt.append((w, a0, s + 0.12 + (du - 0.25) * acc / tot))
    word_times.append(wt)

def captions(img, tt):
    cur = None
    for i, s in enumerate(starts):
        if s - 0.05 <= tt <= s + durs[i] + 0.3: cur = i
    if cur is None: return
    wt = word_times[cur]
    a = clamp((tt - starts[cur] + 0.05) / 0.15) * clamp((starts[cur] + durs[cur] + 0.3 - tt) / 0.15)
    # wrap into rows <= 22 chars
    rows, row = [], []
    for w in wt:
        if sum(len(x[0]) + 1 for x in row) + len(w[0]) > 22 and row:
            rows.append(row); row = []
        row.append(w)
    rows.append(row)
    y = 1450
    dr = ImageDraw.Draw(img)
    for r in rows:
        widths = [dr.textlength(w[0] + " ", font=f_cap) for w in r]
        x = W / 2 - sum(widths) / 2
        for (w, a0, a1), wd in zip(r, widths):
            active = a0 <= tt < a1 + 0.05
            said = tt >= a0
            col = GOLD if active else (CREAM if said else (200, 200, 210))
            pop = 1.0 + (0.08 * (1 - clamp((tt - a0) / 0.18)) if said else 0)
            im = cached_text(f"c{w}{col}", w, f_cap, col + (255,), stroke=6, stroke_fill=(10, 10, 20))
            paste(img, im, x + dr.textlength(w, font=f_cap) / 2, y, a * (1 if said else 0.75), pop)
            x += wd
        y += 82

# ---------------- scenes ----------------
def sc_window(i):
    s0 = starts[i] - 0.2
    s1 = starts[i + 1] - 0.2 if i + 1 < len(starts) else TOTAL + 1
    return s0, s1

def scene(img, i, lt, a, tt):
    dr = ImageDraw.Draw(img)
    cy = 820
    if i == 0:
        kicker(img, "WIGILIA", 560, a)
        p = ease_back(lt / 0.7)
        im = cached_text("2412", "24.12", f_huge, GOLD)
        paste(img, im, W / 2, cy, a, 0.6 + 0.4 * p, glow=(GOLD, 30, 0.6))
        sub = cached_text("s0", "najpiękniejszy wieczór w roku", f_mid, CREAM)
        paste(img, sub, W / 2, cy + 230 + 40 * (1 - ease_out((lt - 0.4) / 0.6)), a * clamp((lt - 0.4) / 0.5))
    elif i == 1:
        r = 150 * ease_back((lt - 0.8) / 1.0)
        if r > 1:
            glow = Image.new("RGBA", (W, H), (0, 0, 0, 0)); gd = ImageDraw.Draw(glow)
            gd.polygon(star_poly(W / 2, 640, r * 1.25), fill=GOLD + (int(150 * a),))
            img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(40)))
            rot = -90 + 8 * math.sin(tt * 1.5)
            dr.polygon(star_poly(W / 2, 640, r, rot=rot), fill=(255, 226, 150, int(255 * a)))
            for k in range(8):  # rays
                ang = math.radians(k * 45 + tt * 20)
                r1, r2 = r * 1.4, r * (1.7 + 0.15 * math.sin(tt * 4 + k))
                dr.line((W/2 + r1*math.cos(ang), 640 + r1*math.sin(ang), W/2 + r2*math.cos(ang), 640 + r2*math.sin(ang)),
                        fill=GOLD + (int(160 * a),), width=5)
        kicker(img, "WYPATRUJEMY", 360, a * clamp(lt / 0.4))
        im = cached_text("pg", "pierwszej\ngwiazdki", f_h, CREAM, spacing=6)
        paste(img, im, W / 2, 1010 + 50 * (1 - ease_out(lt / 0.6)), a * clamp(lt / 0.4))
    elif i == 2:
        kicker(img, "TRADYCJA", 520, a)
        chips = [("biały obrus", 0.0), ("sianko pod obrusem", 1.1), ("puste miejsce przy stole", 2.4)]
        for k, (txt, d0) in enumerate(chips):
            p = ease_back((lt - d0) / 0.5)
            if p <= 0: continue
            im = cached_text("ch" + txt, txt, f_chip, (20, 24, 40))
            bw, bh = im.width + 70, im.height + 44
            chip = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
            ImageDraw.Draw(chip).rounded_rectangle((0, 0, bw - 1, bh - 1), radius=bh // 2,
                                                   fill=[CREAM, GOLD, (255, 255, 255)][k] + (255,))
            chip.alpha_composite(im, (35, 22))
            paste(img, chip, W / 2 + (1 - p) * (-300 if k % 2 else 300), 680 + k * 150, a * clamp(p), 1.0)
    elif i == 3:
        kicker(img, "NAJWAŻNIEJSZY MOMENT", 560, a)
        im = cached_text("op", "Opłatek", f_big, CREAM)
        paste(img, im, W / 2, cy - 20, a, 0.85 + 0.15 * ease_back(lt / 0.6), glow=(CREAM, 25, 0.35))
        im2 = cached_text("op2", "i życzenia prosto z serca", f_mid, GOLD)
        paste(img, im2, W / 2, cy + 140 + 40 * (1 - ease_out((lt - 1.6) / 0.6)), a * clamp((lt - 1.6) / 0.4))
        # wafer hairline split animation
        w = 260 * ease_out((lt - 0.3) / 0.8); gap = 18 * ease_out((lt - 1.8) / 0.5)
        y = cy - 150
        dr.line((W / 2 - w - gap, y, W / 2 - gap, y), fill=GOLD + (int(220 * a),), width=4)
        dr.line((W / 2 + gap, y, W / 2 + w + gap, y), fill=GOLD + (int(220 * a),), width=4)
    elif i == 4:
        n = int(clamp(lt / 1.0) * 11) + 1
        im = cached_text(f"n{n}", str(n), f_huge, GOLD)
        paste(img, im, W / 2, cy - 20, a, 1.0 + 0.12 * (1 - clamp((lt % (1 / 11)) * 11)) if n < 12 else 1.0 + 0.05 * math.sin(lt * 6),
              glow=(GOLD, 30, 0.6))
        im2 = cached_text("pot", "potraw na stole", f_h, CREAM)
        paste(img, im2, W / 2, cy + 230, a * clamp((lt - 0.3) / 0.4))
    elif i == 5:
        kicker(img, "MENU WIGILIJNE", 470, a)
        items = [("barszcz z uszkami", 0.0), ("pierogi", 1.25), ("karp", 1.85), ("makowiec babci", 2.35)]
        for k, (txt, d0) in enumerate(items):
            p = ease_out((lt - d0) / 0.45)
            if p <= 0: continue
            y = 640 + k * 150
            num = cached_text(f"num{k}", f"0{k+1}", f_mid, GOLD)
            it = cached_text("it" + txt, txt, f_chip, CREAM)
            x0 = 170 + (1 - p) * 120
            img_a = a * p
            paste(img, num, x0 + num.width / 2, y, img_a)
            paste(img, it, x0 + 110 + it.width / 2, y, img_a)
            dr.line((x0, y + 55, x0 + (740) * p, y + 55), fill=(255, 255, 255, int(50 * img_a)), width=2)
    elif i == 6:
        # minimalist tree
        g = ease_out(lt / 1.2)
        ty, th = 470, 520 * g
        for k in range(3):
            top = ty + k * th * 0.25
            base = top + th * 0.45
            half = (130 + k * 60) * g
            dr.polygon([(W / 2, top), (W / 2 - half, base), (W / 2 + half, base)], fill=(40, 140, 100, int(235 * a)))
        if g > 0.3:
            dr.polygon(star_poly(W / 2, ty - 10, 42 * g), fill=GOLD + (int(255 * a),))
        lr = np.random.default_rng(11)
        for k in range(26):
            u, v = lr.uniform(0.15, 1), lr.uniform(-1, 1)
            y = ty + u * th * 0.95
            x = W / 2 + v * (u * 300 * g)
            tw = 0.5 + 0.5 * math.sin(tt * 5 + k * 1.7)
            col = [GOLD, RED, CREAM][k % 3]
            rr = 8 + 4 * tw
            dr.ellipse((x - rr, y - rr, x + rr, y + rr), fill=col + (int(255 * a * (0.5 + 0.5 * tw)),))
        words = [("kolędy", 0.0), ("prezenty", 0.9), ("Pasterka", 2.6)]
        for k, (txt, d0) in enumerate(words):
            p = ease_back((lt - d0) / 0.45)
            im = cached_text("kw" + txt, txt, f_mid, [CREAM, CREAM, GOLD][k])
            paste(img, im, W / 2 + (k - 1) * 310, 1140, a * clamp(p), 0.7 + 0.3 * clamp(p))
    elif i == 7:
        im = cached_text("wtn", "Wigilia\nto nie", f_h, CREAM, spacing=8)
        paste(img, im, W / 2, cy - 90, a * clamp(lt / 0.4))
        im2 = cached_text("menu", "menu.", f_big, CREAM)
        paste(img, im2, W / 2, cy + 120, a * clamp((lt - 0.5) / 0.3))
        p = ease_out((lt - 1.0) / 0.4)
        if p > 0:
            x0 = W / 2 - im2.width / 2 - 10
            dr.line((x0, cy + 125, x0 + (im2.width + 20) * p, cy + 115), fill=RED + (int(255 * a),), width=14)
    elif i == 8:
        im = cached_text("tl", "To ludzie", f_big, GOLD)
        paste(img, im, W / 2, cy - 40, a, 0.9 + 0.1 * ease_out(lt / 0.6), glow=(GOLD, 30, 0.5))
        im2 = cached_text("pjs", "przy jednym stole", f_h, CREAM)
        paste(img, im2, W / 2, cy + 120 + 30 * (1 - ease_out((lt - 0.7) / 0.5)), a * clamp((lt - 0.7) / 0.4))
    elif i == 9:
        p = ease_back(lt / 0.8)
        # burst of stars
        for k in range(14):
            ang = k / 14 * 6.283 + 0.3
            rad = 120 + 380 * ease_out(lt / 1.6)
            x, y = W / 2 + rad * math.cos(ang), 820 + rad * math.sin(ang) * 1.1
            al = int(255 * a * clamp(1.6 - lt / 1.5))
            if al > 0:
                dr.polygon(star_poly(x, y, 16 + 6 * (k % 3), rot=lt * 90 + k * 20), fill=[GOLD, CREAM, RED][k % 3] + (al,))
        im = cached_text("ws", "Wesołych\nŚwiąt!", f_big, GOLD, spacing=10)
        paste(img, im, W / 2, 800, a, 0.5 + 0.5 * p, glow=(GOLD, 35, 0.7))
        im2 = cached_text("ws2", "spokoju  ·  bliskości  ·  smacznego", f_mid, CREAM)
        paste(img, im2, W / 2, 1100, a * clamp((lt - 1.0) / 0.5))
        im3 = cached_text("tags", "#wigilia  #święta  #tradycja", f_small, (200, 200, 215))
        paste(img, im3, W / 2, 1640, a * clamp((lt - 1.5) / 0.5))

# ---------------- render ----------------
ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                       "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                       "-pix_fmt", "yuv420p", "video_noaudio.mp4"], stdin=subprocess.PIPE)
preview = {int(starts[i] * FPS + 1.6 * FPS) for i in range(len(starts))}
for fi in range(NF):
    tt = fi / FPS
    mix = 0.5 + 0.5 * math.sin(tt * 0.25)
    bg = (BG_A * (1 - mix * 0.5) + BG_B * mix * 0.5).astype(np.uint8)
    img = Image.fromarray(bg).convert("RGBA")
    ox = int((BW - W) / 2 + 60 * math.sin(tt * 0.3)); oy = int((BH - H) / 2 + 80 * math.cos(tt * 0.22))
    img.alpha_composite(bokeh.crop((ox, oy, ox + W, oy + H)))
    dr = ImageDraw.Draw(img)
    # snow
    speed = 1.0 + (1.2 if tt > starts[9] else 0)
    for x, y0, s, ph in snow:
        y = (y0 + tt * s * 38 * speed) % (H + 40) - 20
        xx_ = x + 22 * math.sin(tt * 0.8 + ph)
        dr.ellipse((xx_ - s, y - s, xx_ + s, y + s), fill=(255, 255, 255, int(40 + s * 28)))
    for i in range(len(starts)):
        s0, s1 = sc_window(i)
        if s0 <= tt < s1 + 0.25:
            a = clamp((tt - s0) / 0.3) * clamp((s1 + 0.05 - tt) / 0.3)
            if i == len(starts) - 1:
                a = clamp((tt - s0) / 0.3)
            scene(img, i, tt - starts[i], a, tt)
    captions(img, tt)
    img.alpha_composite(VIG)
    # progress bar + fade out
    dr = ImageDraw.Draw(img)
    dr.rectangle((0, 0, int(W * tt / TOTAL), 7), fill=GOLD + (230,))
    out = img.convert("RGB")
    fade = clamp((TOTAL - tt) / 0.8) * clamp(tt / 0.4)
    if fade < 1:
        out = Image.eval(out, lambda v: int(v * fade))
    if fi in preview:
        out.resize((W // 3, H // 3)).save(f"prev_{fi:04d}.png")
    ff.stdin.write(out.tobytes())
    if fi % 150 == 0: print(f"frame {fi}/{NF}", flush=True)
ff.stdin.close(); ff.wait()
print("video ok", TOTAL)
