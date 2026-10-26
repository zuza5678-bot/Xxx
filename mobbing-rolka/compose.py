"""Rolka o mobbingu (9:16, 1080x1920, 30 fps): fotorealistyczne kadry z ruchem kamery,
napisy pojawiające się w rytmie historii, plansza końcowa i muzyka w tle.

Wejście:  assets/scene1..4.(png|jpg), assets/music.mp3 (opcjonalnie)
Wyjście:  mobbing_rolka.mp4
"""
import glob
import math
import os
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1920
FPS = 30
HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")
OUT = os.path.join(HERE, "mobbing_rolka.mp4")
FONT_B = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
FONT_R = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
XFADE = 0.7

# (plik, czas trwania, zoom od->do, środek kadru od->do jako ułamek obrazu źródłowego)
# sceny 1 i 3 są poziome: kamera przesuwa się po nich jak panorama w pionowym kadrze
SCENES = [
    ("scene1", 6.0, (1.05, 1.12), ((0.80, 0.42), (0.38, 0.40))),   # szepczący -> ona
    ("scene2", 6.0, (1.14, 1.03), ((0.50, 0.50), (0.50, 0.46))),
    ("scene3", 6.5, (1.02, 1.12), ((0.47, 0.60), (0.41, 0.52))),
    ("scene4", 6.0, (1.03, 1.12), ((0.50, 0.50), (0.50, 0.45))),
]
END_CARD = 5.0
DUR = sum(s[1] for s in SCENES) - XFADE * (len(SCENES) - 1) + END_CARD

# (od, do, tekst, styl) — styl: "line" zwykły napis, "big" mocny akcent
CAPTIONS = [
    (0.6, 2.9, "Codziennie te same szepty.", "line"),
    (3.0, 5.4, "Celowe pomijanie. Izolowanie.", "line"),
    (5.9, 8.4, "Krytyka przy wszystkich.", "line"),
    (8.5, 11.0, "Ośmieszanie. Odbieranie zadań.", "line"),
    (11.5, 14.0, "Bezsenność.\nLęk przed poniedziałkiem.", "line"),
    (14.3, 17.0, "To nie jest „taki styl zarządzania”.", "line"),
    (15.6, 17.0, "TO JEST MOBBING.", "big"),
    (17.6, 20.0, "Nie musisz tego znosić w samotności.", "line"),
    (20.1, 22.6, "Dokumentuj. Szukaj wsparcia. Zgłaszaj.", "line"),
]


def lerp(a, b, t):
    return a + (b - a) * t


def ease(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


def load_scene(name):
    path = sorted(glob.glob(os.path.join(ASSETS, name + ".*")))[0]
    im = Image.open(path).convert("RGB")
    # wypełnij kadr 9:16 z zapasem na ruch kamery
    scale = max(W / im.width, H / im.height) * 1.25
    return im.resize((int(im.width * scale), int(im.height * scale)), Image.LANCZOS)


def ken_burns(im, t, zooms, pan):
    z = lerp(zooms[0], zooms[1], ease(t))
    # obraz pokrywa co najmniej 1.25x kadru; wycinek 1.2x/z zostawia zapas na przesunięcie
    cw = W * 1.2 / z
    ch = cw * H / W
    (x0, y0), (x1, y1) = pan
    cx = lerp(x0, x1, ease(t)) * im.width
    cy = lerp(y0, y1, ease(t)) * im.height
    cx = min(max(cx, cw / 2), im.width - cw / 2)
    cy = min(max(cy, ch / 2), im.height - ch / 2)
    return im.resize((W, H), Image.BICUBIC, box=(cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2))


def grade(arr, warmth):
    """Lekko zdesaturowany, chłodny grade; warmth 0..1 ociepla końcówkę."""
    lum = arr.mean(axis=2, keepdims=True)
    arr = lum + (arr - lum) * lerp(0.72, 0.95, warmth)
    tint = np.array([lerp(0.96, 1.04, warmth), 1.0, lerp(1.05, 0.95, warmth)], np.float32)
    return arr * tint


def wrap(dr, txt, fnt, maxw):
    lines = []
    for para in txt.split("\n"):
        cur = ""
        for word in para.split(" "):
            test = (cur + " " + word).strip()
            if dr.textlength(test, font=fnt) <= maxw:
                cur = test
            else:
                lines.append(cur)
                cur = word
        lines.append(cur)
    return lines


def draw_caption(img, txt, style, age, left):
    a = min(1.0, age / 0.45, left / 0.35)
    if a <= 0:
        return
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    dr = ImageDraw.Draw(layer)
    if style == "big":
        fnt = ImageFont.truetype(FONT_B, 88)
        y0 = 760
        color = (255, 255, 255)
    else:
        fnt = ImageFont.truetype(FONT_B, 62)
        y0 = 1290
        color = (255, 255, 255)
    lines = wrap(dr, txt, fnt, W - (100 if style == "big" else 180))
    lh = fnt.size * 1.22
    rise = (1 - ease(age / 0.45)) * 24
    for i, ln in enumerate(lines):
        tw = dr.textlength(ln, font=fnt)
        x = (W - tw) / 2
        y = y0 + i * lh + rise
        if style == "big":
            pad = 26
            dr.rectangle([x - pad, y - 14, x + tw + pad, y + fnt.size + 18], fill=(170, 20, 30, int(235 * a)))
        else:
            for dx, dy, al in ((0, 3, 160), (0, 0, 60)):
                dr.text((x + dx, y + dy), ln, font=fnt, fill=(0, 0, 0, int(al * a)))
        dr.text((x, y), ln, font=fnt, fill=color + (int(255 * a),))
    if style == "line":
        shadow = layer.filter(ImageFilter.GaussianBlur(6))
        img.alpha_composite(shadow)
    img.alpha_composite(layer)


def end_card(t_local):
    img = Image.new("RGBA", (W, H), (12, 12, 16, 255))
    dr = ImageDraw.Draw(img)
    a1 = ease(t_local / 0.6)
    a2 = ease((t_local - 0.8) / 0.6)
    a3 = ease((t_local - 1.6) / 0.6)
    f_big = ImageFont.truetype(FONT_B, 92)
    f_mid = ImageFont.truetype(FONT_R, 46)
    f_sm = ImageFont.truetype(FONT_B, 50)
    f_xs = ImageFont.truetype(FONT_R, 36)

    def center(txt, y, f, col, a):
        tw = dr.textlength(txt, font=f)
        dr.text(((W - tw) / 2, y), txt, font=f, fill=tuple(int(c * a + 12 * (1 - a)) for c in col))

    center("Mobbing to nie", 640, f_big, (255, 255, 255), a1)
    center("Twoja wina.", 750, f_big, (230, 60, 70), a1)
    dr.rectangle([W / 2 - 60, 900, W / 2 + 60, 906], fill=tuple(int(c * a2 + 12 * (1 - a2)) for c in (230, 60, 70)))
    center("Pracodawca ma obowiązek", 960, f_mid, (225, 225, 225), a2)
    center("przeciwdziałać mobbingowi.", 1020, f_mid, (225, 225, 225), a2)
    center("art. 94³ Kodeksu pracy", 1085, f_xs, (160, 160, 165), a2)
    center("Bezpłatne porady PIP:", 1230, f_mid, (225, 225, 225), a3)
    center("801 002 006  ·  459 599 000", 1295, f_sm, (255, 255, 255), a3)
    center("Udostępnij — ktoś może tego potrzebować.", 1480, f_xs, (170, 170, 175), a3)
    return img


def vignette():
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H / 2) / (H * 0.6)) ** 2)
    return (1 - np.clip(d - 0.55, 0, 1) * 0.75)[..., None].astype(np.float32)


def scene_frame(images, t):
    """Klatka z sekwencji scen z przenikaniem XFADE między nimi."""
    starts, s = [], 0.0
    for _, d, _, _ in SCENES:
        starts.append(s)
        s += d - XFADE
    out = None
    for i, ((_, d, z, pan), st) in enumerate(zip(SCENES, starts)):
        if st <= t < st + d:
            fr = np.asarray(ken_burns(images[i], (t - st) / d, z, pan), np.float32)
            w = 1.0
            if i > 0 and t < st + XFADE:
                w = (t - st) / XFADE
            out = fr if out is None else out * (1 - w) + fr * w
    return out


def main():
    images = [load_scene(n) for n, *_ in SCENES]
    vig = vignette()
    rng = np.random.default_rng(7)
    scenes_end = DUR - END_CARD

    music = os.path.join(ASSETS, "music.mp3")
    if not os.path.exists(music):
        music = os.path.join(ASSETS, "music_synth.wav")
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-"]
    if os.path.exists(music):
        cmd += ["-i", music, "-filter_complex",
                f"[1:a]atrim=0:{DUR},afade=t=in:d=1,afade=t=out:st={DUR - 2.0}:d=2.0,volume=0.9[a]",
                "-map", "0:v", "-map", "[a]", "-c:a", "aac", "-b:a", "192k"]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
            "-t", f"{DUR}", "-movflags", "+faststart", OUT]
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    n = int(DUR * FPS)
    for f in range(n):
        t = f / FPS
        if t < scenes_end:
            arr = scene_frame(images, t)
            warmth = ease((t - 16.8) / 1.5)
            arr = grade(arr, warmth) * vig
            # krótkie przyciemnienie przy "TO JEST MOBBING."
            arr *= 1 - 0.35 * math.exp(-((t - 15.9) / 0.6) ** 2)
            frame = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA")
            for c0, c1, txt, style in CAPTIONS:
                if c0 <= t < c1:
                    draw_caption(frame, txt, style, t - c0, c1 - t)
            fade_out = ease((t - (scenes_end - 0.6)) / 0.6)
            fade_in = ease(t / 0.8)
            k = fade_in * (1 - fade_out)
        else:
            frame = end_card(t - scenes_end)
            k = min(1.0, (DUR - t) / 0.8)
        arr = np.asarray(frame.convert("RGB"), np.float32) * k
        arr += rng.normal(0, 3.5, size=(H, W, 1))
        ff.stdin.write(np.clip(arr, 0, 255).astype(np.uint8).tobytes())
        if f % 90 == 0:
            print(f"klatka {f}/{n}", flush=True)
    ff.stdin.close()
    ff.wait()
    print("Gotowe:", OUT)


if __name__ == "__main__":
    main()
