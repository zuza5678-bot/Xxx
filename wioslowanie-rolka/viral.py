"""Wiralowa wersja rolki: hak "POV: budzik 4:45", drop, sprint, slow-motion na mecie, CTA.

Uruchomienie:  python3 viral.py  ->  wioslowanie_viral.mp4
Korzysta ze scenografii i kinematyki z render.py.
"""
import math
import os
import random
import subprocess
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import render as R
from render import W, H, FPS, DRIVE, LAYER_Y0, LAYER_H, WATERLINE, STATIONS, S, lerp, smooth

DUR = 12.0
NFRAMES = int(DUR * FPS)
OUT = os.path.join(R.HERE, "wioslowanie_viral.mp4")
DROP = 1.6          # wschód słońca + wejście bitu
SPRINT_END = 9.0    # meta
EMOJI_FONT = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
SR = R.SR


# ---------------------------------------------------------------- oś czasu

def warp(t):
    """Tempo upływu czasu sceny względem czasu filmu (slow-motion na mecie)."""
    if SPRINT_END <= t < SPRINT_END + 1.0:
        return 0.3
    if t >= SPRINT_END + 1.0:
        return 0.6
    return 1.0


def rate(t):
    """Tempo wiosłowania (uderzenia / min)."""
    if t < DROP:
        return 20.0
    if t < SPRINT_END:
        return lerp(32, 44, smooth(DROP, SPRINT_END - 0.5, t))
    return 30.0


def phase_curve(step):
    ts = np.arange(0, DUR + 1, step)
    dp = np.array([rate(t) / 60.0 * warp(t) for t in ts]) * step
    ph = np.concatenate([[0.0], np.cumsum(dp)[:-1]])
    ph -= np.interp(DROP, ts, ph)          # chwyt dokładnie na dropie
    return ts, ph


# ---------------------------------------------------------------- łódź

def render_boat(p, ox):
    layer = Image.new("RGBA", (W * S, LAYER_H * S), (0, 0, 0, 0))
    dr = ImageDraw.Draw(layer)
    poses = [R.rower_pose(sx, p) for sx in STATIONS]
    for i, (sx, pose) in enumerate(zip(STATIONS, poses)):
        if i % 2 == 1:
            R.draw_oar(dr, sx, pose, ox, near=False)
    R.draw_hull(dr, ox)
    for sx, pose in zip(STATIONS, poses):
        R.draw_rower(dr, sx, pose, ox)
    for i, (sx, pose) in enumerate(zip(STATIONS, poses)):
        if i % 2 == 0:
            R.draw_oar(dr, sx, pose, ox, near=True)
    return layer.resize((W, LAYER_H), Image.LANCZOS), poses


def boat_speed(p, spm):
    surge = math.sin(min(p / (DRIVE + 0.12), 1.0) * math.pi)
    return (240 + 160 * surge) * spm / 30.0


# ---------------------------------------------------------------- napisy w stylu TikToka

_fonts = {}


def fnt(size, bold=True):
    key = (size, bold)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(R.FONT_B if bold else R.FONT_R, size)
    return _fonts[key]


_emoji = {}


def emoji(ch, size):
    key = (ch, size)
    if key not in _emoji:
        f = ImageFont.truetype(EMOJI_FONT, 109)
        im = Image.new("RGBA", (140, 140), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((4, 4), ch, font=f, embedded_color=True)
        im = im.crop(im.getbbox())
        _emoji[key] = im.resize((size, int(size * im.height / im.width)), Image.LANCZOS)
    return _emoji[key]


def pop(age):
    """Skala "wyskakującego" napisu: szybki overshoot i powrót do 1."""
    if age < 0:
        return 0.0
    if age < 0.12:
        return lerp(0.4, 1.18, age / 0.12)
    if age < 0.22:
        return lerp(1.18, 1.0, (age - 0.12) / 0.1)
    return 1.0


def caption(img, txt, cy, size, t, t_in, t_out, color=(255, 255, 255), emo=None, box=None):
    if not (t_in <= t < t_out):
        return
    sc = pop(t - t_in)
    out_a = min(1.0, (t_out - t) / 0.12)
    sz = max(8, int(size * sc))
    f = fnt(sz)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    dr = ImageDraw.Draw(layer)
    tw = dr.textlength(txt, font=f)
    ew = int(sz * 1.05) if emo else 0
    total = tw + (ew + sz * 0.2 if emo else 0)
    x = (W - total) / 2
    y = cy - sz / 2
    if box:
        pad = sz * 0.28
        dr.rounded_rectangle([x - pad, y - pad * 0.6, x + total + pad, y + sz * 1.05 + pad * 0.6],
                             radius=int(sz * 0.25), fill=box)
    dr.text((x, y), txt, font=f, fill=(15, 15, 25) if box else color, stroke_width=max(2, sz // 12) if not box else 0,
            stroke_fill=(0, 0, 0))
    if emo:
        e = emoji(emo, ew)
        layer.alpha_composite(e, (int(x + tw + sz * 0.2), int(y + sz * 0.5 - e.height / 2)))
    if out_a < 1:
        layer.putalpha(layer.getchannel("A").point(lambda v: int(v * out_a)))
    img.alpha_composite(layer)


CAPTIONS = [
    # (od, do, tekst, środek_y, rozmiar, emoji, tło)
    (0.05, DROP, "POV:", 330, 110, None, None),
    (0.45, DROP, "budzik 4:45", 470, 120, "⏰", None),
    (DROP + 0.25, 3.3, "znajomi:", 330, 96, None, None),
    (DROP + 0.65, 3.3, "śpią", 460, 120, "😴", None),
    (3.3, 4.8, "ty:", 330, 110, None, None),
    (3.65, 4.8, "o świcie na wodzie", 460, 92, "🌅", None),
    (SPRINT_END + 0.05, SPRINT_END + 1.0, "META", 420, 190, None, None),
    (SPRINT_END + 1.05, DUR, "warto było?", 330, 100, None, None),
    (SPRINT_END + 1.75, DUR, "zawsze.", 470, 140, "🔥", None),
    (SPRINT_END + 2.2, DUR, "oznacz kogoś, kto by nie wstał", 1500, 46, "👇", (255, 255, 255, 235)),
]


def draw_sprint_hud(img, t, spm_shown, catch_age, meters):
    if not (4.8 <= t < SPRINT_END):
        return
    a = min(1.0, (t - 4.8) / 0.2, (SPRINT_END - t) / 0.1)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    dr = ImageDraw.Draw(layer)
    # pasek postępu do mety
    x0, x1, y = 90, W - 90, 210
    prog = smooth(4.8, SPRINT_END, t)
    dr.rounded_rectangle([x0, y, x1, y + 26], radius=13, fill=(0, 0, 0, int(140 * a)))
    dr.rounded_rectangle([x0, y, x0 + max(26, (x1 - x0) * prog), y + 26], radius=13, fill=(255, 70, 80, int(255 * a)))
    f = fnt(38)
    lab = f"OSTATNIE 500 M  ·  {meters} m"
    dr.text(((W - dr.textlength(lab, font=f)) / 2, y - 60), lab, font=f, fill=(255, 255, 255, int(255 * a)),
            stroke_width=3, stroke_fill=(0, 0, 0, int(200 * a)))
    img.alpha_composite(layer)
    # duży licznik tempa, podbija na każdym chwycie
    sc = 1.0 + 0.22 * math.exp(-catch_age * 9)
    caption(img, "TEMPO", 360, 52, t, 4.8, SPRINT_END)
    caption(img, f"{spm_shown}", 520, int(230 * sc), t, t - 1, t + 1,
            color=(255, 235, 120) if spm_shown >= 40 else (255, 255, 255))


# ---------------------------------------------------------------- kamera i efekty

def camera(frame, zoom, shake, rnd, focus=(W / 2, 1150)):
    if zoom <= 1.001 and shake < 0.5:
        return frame
    dx, dy = rnd.uniform(-shake, shake), rnd.uniform(-shake, shake)
    cw, ch = W / zoom, H / zoom
    cx = min(max(focus[0] + dx, cw / 2), W - cw / 2)
    cy = min(max(focus[1] + dy, ch / 2), H - ch / 2)
    box = (cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)
    return frame.resize((W, H), Image.BILINEAR, box=box)


def speed_lines(img, intensity, rnd):
    if intensity <= 0:
        return
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    dr = ImageDraw.Draw(layer)
    for _ in range(int(28 * intensity)):
        y = rnd.uniform(0, H)
        if 700 < y < 1350 and rnd.random() < 0.8:
            continue
        x = rnd.uniform(-200, W)
        ln = rnd.uniform(150, 500)
        dr.line([(x, y), (x + ln, y)], fill=(255, 255, 255, int(rnd.uniform(40, 120) * intensity)), width=rnd.choice([2, 3, 4]))
    img.alpha_composite(layer)


# ---------------------------------------------------------------- audio

def build_audio(path, ts, ph):
    n = int(DUR * SR)
    out = np.zeros(n, np.float32)
    rng = np.random.default_rng(2)

    def add(sig, t0, gain=1.0):
        i = int(t0 * SR)
        if i >= n or i + len(sig) <= 0:
            return
        j = min(n, i + len(sig))
        out[max(i, 0):j] += sig[max(0, -i):j - i] * gain

    def tone(freq, length, kind="sine"):
        tt = np.arange(int(length * SR)) / SR
        x = np.sin(2 * np.pi * freq * tt)
        if kind == "square":
            x = np.sign(x) * 0.6
        if kind == "saw":
            x = 2 * ((freq * tt) % 1) - 1
        return x.astype(np.float32)

    kn = int(0.5 * SR)
    kt = np.arange(kn) / SR
    kick = (np.sin(2 * np.pi * (42 * kt + 140 * (1 - np.exp(-kt * 28)) / 28)) * np.exp(-kt * 6)).astype(np.float32)
    hn = int(0.05 * SR)
    hat = np.diff(rng.standard_normal(hn), prepend=0).astype(np.float32) * R.env(hn, 0.001, 0.012)
    cn = int(0.25 * SR)
    clap = np.convolve(rng.standard_normal(cn), np.ones(3) / 3, mode="same").astype(np.float32) * R.env(cn, 0.002, 0.06)
    sn = int(0.5 * SR)
    splash = np.convolve(rng.standard_normal(sn), np.ones(6) / 6, mode="same").astype(np.float32) * R.env(sn, 0.004, 0.1)

    # intro: budzik + przyciszony pad + narastający riser
    for b0 in (0.15, 0.95):
        for k in range(4):
            beep = tone(2100, 0.07, "square") * R.env(int(0.07 * SR), 0.002, 0.05)
            add(beep, b0 + k * 0.11, 0.22)
    rl = int(1.0 * SR)
    rt = np.arange(rl) / SR
    riser = np.convolve(rng.standard_normal(rl), np.ones(4) / 4, mode="same") * (rt / 1.0) ** 2
    riser += np.sin(2 * np.pi * (200 * rt + 600 * rt ** 2)) * (rt / 1.0) ** 2 * 0.5
    add(riser.astype(np.float32), DROP - 1.0, 0.35)
    pad_chord = (57, 60, 64)
    pl = int(DROP * SR)
    pt = np.arange(pl) / SR
    pad = sum(np.sin(2 * np.pi * R.note_hz(m) * pt) for m in pad_chord) * np.minimum(pt / 0.3, 1)
    add(pad.astype(np.float32), 0, 0.05)

    # drop: uderzenie + crash
    crn = int(1.2 * SR)
    crash = rng.standard_normal(crn).astype(np.float32) * R.env(crn, 0.001, 0.35)
    add(kick, DROP, 1.6)
    add(crash, DROP, 0.35)

    # bit zsynchronizowany z fazą wiosłowania: 4 stopy na cykl, rośnie razem z tempem
    bass_seq = [45, 45, 41, 43]
    grid = np.arange(math.floor(ph.min() * 4), math.ceil(ph.max() * 4) + 1) / 4.0
    for g in grid:
        tq = float(np.interp(g, ph, ts))
        if not (DROP <= tq < SPRINT_END - 0.02):
            continue
        q = int(round(g * 4)) % 4
        stroke = int(math.floor(g + 1e-6))
        add(kick, tq, 1.0 if q == 0 else 0.7)
        if q in (1, 3):
            add(clap, tq, 0.35)
        tq_next = float(np.interp(g + 0.25, ph, ts))
        add(hat, (tq + tq_next) / 2, 0.3)
        if q == 0:
            add(splash, tq + 0.01, 0.4)
            dur = float(np.interp(g + 1, ph, ts)) - tq
            b = np.tanh(3 * tone(R.note_hz(bass_seq[stroke % 4]), dur)) * R.env(int(dur * SR), 0.005, dur * 0.8)
            add(b.astype(np.float32), tq, 0.22)
            lead = tone(R.note_hz(bass_seq[stroke % 4] + 24), min(dur, 0.25), "saw") * R.env(int(min(dur, 0.25) * SR), 0.003, 0.08)
            add(lead, tq, 0.05 + 0.05 * smooth(DROP, SPRINT_END, tq))

    # meta: cięcie, potężne uderzenie z ogonem, potem spokojny akord
    boom_l = int(2.5 * SR)
    bt = np.arange(boom_l) / SR
    boom = (np.sin(2 * np.pi * (35 * bt + 90 * (1 - np.exp(-bt * 10)) / 10)) * np.exp(-bt * 1.6)).astype(np.float32)
    add(boom, SPRINT_END, 1.8)
    add(crash, SPRINT_END, 0.5)
    ol = int((DUR - SPRINT_END - 1.0) * SR)
    ot = np.arange(ol) / SR
    outro = sum(np.sin(2 * np.pi * R.note_hz(m) * ot) + 0.3 * np.sin(2 * np.pi * R.note_hz(m) * 2.002 * ot)
                for m in (53, 57, 60, 64)) * np.minimum(ot / 0.4, 1)
    add(outro.astype(np.float32), SPRINT_END + 1.0, 0.06)
    add(kick, SPRINT_END + 1.75, 1.0)
    add(crash, SPRINT_END + 1.75, 0.2)

    fo = int(0.6 * SR)
    out[-fo:] *= np.linspace(1, 0, fo)
    out = np.tanh(out * 1.3)
    out /= max(1e-6, np.abs(out).max()) / 0.9
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes((out * 32767).astype(np.int16).tobytes())


# ---------------------------------------------------------------- main

def main(preview=None):
    ts, ph = phase_curve(1.0 / SR * 20)
    wav = os.path.join(R.HERE, "_viral.wav")
    if preview is None:
        build_audio(wav, ts, ph)

    bg = R.build_background().convert("RGBA")
    far, far_h = R.build_strip(3000, R.HORIZON - 170, 40, (92, 62, 110, 255), 11)
    near, near_h = R.build_strip(3000, R.HORIZON - 120, 22, (44, 32, 66, 255), 23, trees=True)

    ff = None
    if preview is None:
        ff = subprocess.Popen([
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
            "-i", wav,
            "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", OUT,
        ], stdin=subprocess.PIPE)

    fx = R.Effects()
    rnd = random.Random(9)
    grain = np.random.default_rng(4)
    scroll = 0.0
    dt = 1.0 / FPS
    last_catch_t = -10.0
    spm_shown = 32
    prev_stroke = None
    for f in range(NFRAMES):
        t = f * dt
        phase = float(np.interp(t, ts, ph))
        p = phase % 1.0
        stroke = math.floor(phase)
        if prev_stroke is not None and stroke != prev_stroke:
            last_catch_t = t
            spm_shown = int(round(rate(t)))
        prev_stroke = stroke
        spm = rate(t)
        v = boat_speed(p, spm)
        sim_dt = dt * warp(t)
        scroll += v * sim_dt

        if preview is not None and f not in preview:
            fx.update(sim_dt, p, [R.rower_pose(sx, p) for sx in STATIONS], scroll, W / 2)
            continue

        frame = bg.copy()
        for strip, sh, par in ((far, far_h, 0.04), (near, near_h, 0.12)):
            off = int(scroll * par) % strip.width
            y = R.HORIZON - sh + 40
            frame.alpha_composite(strip.crop((off, 0, min(off + W, strip.width), sh)), (0, y))
            if off + W > strip.width:
                frame.alpha_composite(strip.crop((0, 0, off + W - strip.width, sh)), (strip.width - off, y))
        frame.paste(bg.crop((0, R.HORIZON, W, R.HORIZON + 50)), (0, R.HORIZON))
        dr = ImageDraw.Draw(frame)
        R.draw_water_detail(dr, scroll, t, f // 3)
        R.draw_buoys(dr, scroll)

        boat_ox = W / 2 - 10 * math.sin(p * 2 * math.pi)
        boat, poses = render_boat(p, boat_ox)
        above = boat.crop((0, 0, W, WATERLINE - LAYER_Y0))
        refl = above.transpose(Image.FLIP_TOP_BOTTOM).filter(ImageFilter.GaussianBlur(3))
        rr, gg, bb, aa = refl.split()
        refl = Image.merge("RGBA", (rr.point(lambda x: x // 2), gg.point(lambda x: x // 2),
                                    bb.point(lambda x: int(x * 0.7)), aa.point(lambda x: int(x * 0.3))))
        frame.alpha_composite(refl, (0, WATERLINE + 4))
        fx.update(sim_dt, p, poses, scroll, boat_ox)
        fx.draw(dr, scroll)
        frame.alpha_composite(boat, (0, LAYER_Y0))

        # kamera: punch-in na dropie, coraz bliżej w sprincie, podbicie na każdym chwycie
        catch_age = t - last_catch_t
        if t < DROP:
            zoom, shake = 1.0 + 0.04 * t / DROP, 0.0
        elif t < SPRINT_END:
            zoom = lerp(1.08, 1.32, smooth(DROP, SPRINT_END, t)) + 0.18 * math.exp(-(t - DROP) * 5)
            zoom += 0.035 * math.exp(-catch_age * 8)
            shake = lerp(1, 9, smooth(4.8, SPRINT_END, t))
        elif t < SPRINT_END + 1.0:
            zoom, shake = lerp(1.45, 1.2, (t - SPRINT_END)), 0.0
        else:
            zoom, shake = lerp(1.2, 1.0, smooth(SPRINT_END + 1, DUR, t)), 0.0
        frame = camera(frame, zoom, shake, rnd)
        speed_lines(frame, smooth(4.8, 6.5, t) * (t < SPRINT_END), rnd)

        arr = np.asarray(frame.convert("RGB"), dtype=np.float32)
        # przed świtem: ciemno i chłodno, na dropie "wschód słońca w jednym pociągnięciu"
        night = 1 - smooth(DROP - 0.05, DROP + 0.5, t)
        if night > 0:
            lum = arr.mean(axis=2, keepdims=True)
            cold = lum * np.array([0.35, 0.42, 0.75], np.float32)
            arr = arr * (1 - night) + cold * night
        # błysk na dropie i na mecie
        flash = max(math.exp(-max(0, t - DROP) * 9) * (t >= DROP), math.exp(-max(0, t - SPRINT_END) * 6) * (t >= SPRINT_END))
        if flash > 0.01:
            arr = arr + (255 - arr) * flash * 0.85
        frame = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA")
        for c in CAPTIONS:
            caption(frame, c[2], c[3], c[4], t, c[0], c[1], emo=c[5], box=c[6])
        meters = max(0, int(round(500 * (1 - smooth(4.8, SPRINT_END, t)))))
        draw_sprint_hud(frame, t, spm_shown, catch_age, meters)

        arr = np.asarray(frame.convert("RGB"), dtype=np.float32)
        arr += grain.integers(-5, 6, size=(H, W, 1))
        arr = np.clip(arr, 0, 255).astype(np.uint8)
        if preview is not None:
            Image.fromarray(arr).resize((405, 720)).save(os.path.join(preview_dir, f"v{f}.png"))
            continue
        ff.stdin.write(arr.tobytes())
        if f % 60 == 0:
            print(f"klatka {f}/{NFRAMES}", flush=True)

    if ff:
        ff.stdin.close()
        ff.wait()
        os.remove(wav)
        print("Gotowe:", OUT)


preview_dir = None

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2 and sys.argv[1] == "--preview":
        preview_dir = sys.argv[2]
        main(preview={int(x) for x in sys.argv[3].split(",")})
    else:
        main()
