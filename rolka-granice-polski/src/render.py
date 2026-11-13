import os, sys, json, math, re, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
sys.path.insert(0, os.path.dirname(__file__))
from scenes import SCENES
from timeline import build, FPS, S

W, H = 1080, 1920
MAP_Y0, MAP_Y1 = 500, 1440
MW, MH = W, MAP_Y1 - MAP_Y0
RED = (220, 20, 60)
RED_HI = (255, 77, 106)
FD = '/usr/share/fonts/opentype/inter/'
def F(name, size): return ImageFont.truetype(FD + name, size)
F_YEAR = F('Inter-ExtraBold.otf', 210)
F_BIG = F('Inter-ExtraBold.otf', 116)
F_TITLE = F('Inter-SemiBold.otf', 52)
F_KICK = F('Inter-SemiBold.otf', 28)
F_SUB = F('Inter-Bold.otf', 50)
F_TL = F('Inter-Medium.otf', 22)
F_TLB = F('Inter-Bold.otf', 25)
LABEL_FONTS = {s: F('Inter-Bold.otf', s) for s in (34, 36, 38)}

TL, TOTAL = build()
NFRAMES = int(math.ceil(TOTAL * FPS))
SC = {s['key']: s for s in SCENES}
META = json.load(open(f'{S}/layers/meta.json'))
LX0, LY1, LKM, LW, LH = META['X0'], META['Y1'], META['KM'], META['W'], META['H']
YEARS = [s['year'] for s in SCENES if s['year']]

def ease(x): x = min(1, max(0, x)); return x * x * (3 - 2 * x)
def ease_out(x): x = min(1, max(0, x)); return 1 - (1 - x) ** 3

# ---------- camera ----------
def fit_cam(key):
    m = META['scenes'][key]
    if key == '1795' or key == '1772':
        b = (-230, -460, 1150, 720)
    elif key == '1945':
        b = (-330, -450, 900, 600)
    else:
        b = m.get('bounds', (-330, -450, 900, 600))
    cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
    km = max((b[2] - b[0]) / (MW * 0.62), (b[3] - b[1]) / (MH * 0.62))
    km = min(3.2, max(1.75, km))
    return [cx, cy, km]
CAMS = {s['key']: fit_cam(s['key']) for s in SCENES}
CAMS['intro_start'] = [-450, 150, 3.8]
CAMS['outro'] = [150, 120, 3.5]

def camera(t):
    for i, s in enumerate(TL):
        if s['start'] <= t < s['end'] or i == len(TL) - 1:
            break
    k = s['key']
    tgt = CAMS[k]
    if k == 'intro':
        a = ease((t - 0.3) / 8.0)
        src = CAMS['intro_start']
        c = [src[j] + (tgt[j] - src[j]) * a for j in range(3)]
    else:
        prev = TL[i - 1]['key']
        p = CAMS[prev]
        p = [p[0], p[1], p[2] * 0.965]  # end of previous drift
        a = ease((t - s['start']) / (2.4 if k == 'outro' else 1.3))
        c = [p[j] + (tgt[j] - p[j]) * a for j in range(3)]
        drift = (t - s['start']) / max(1, s['end'] - s['start'])
        if k != 'outro':
            c[2] *= 1 - 0.035 * drift
    return c, i

# ---------- layers ----------
_lay = {}
def layer(key):
    if key not in _lay:
        if len(_lay) > 3: _lay.pop(next(iter(_lay)))
        _lay[key] = Image.open(f'{S}/layers/{key}.png').convert('RGBA')
    return _lay[key]

def crop_map(key, cam):
    cx, cy, km = cam
    wkm, hkm = MW * km, MH * km
    x0 = (cx - wkm / 2 - LX0) / LKM; y0 = (LY1 - (cy + hkm / 2)) / LKM
    w, h = wkm / LKM, hkm / LKM
    x0 = min(max(0, x0), LW - w); y0 = min(max(0, y0), LH - h)
    im = layer(key).resize((MW, MH), Image.BILINEAR, box=(x0, y0, x0 + w, y0 + h))
    return im, (x0, y0, w / MW)

def to_screen(xy, view):
    x0, y0, s = view
    px = ((xy[0] - LX0) / LKM - x0) / s
    py = ((LY1 - xy[1]) / LKM - y0) / s
    return px, py + MAP_Y0

# feather mask for map
def make_feather():
    yy, xx = np.mgrid[0:MH, 0:MW].astype(np.float32)
    fx = np.clip(np.minimum(xx, MW - 1 - xx) / 170, 0, 1)
    fy = np.clip(np.minimum(yy, MH - 1 - yy) / 210, 0, 1)
    f = (np.sin(fx * np.pi / 2) * np.sin(fy * np.pi / 2)) ** 1.2
    return f
FEATHER = make_feather()

# ---------- flag ----------
FW, FH = 540, 960
fy_, fx_ = np.mgrid[0:FH, 0:FW].astype(np.float32)
def flag(t):
    u = fx_ / FW; v = fy_ / FH
    ph = 2 * math.pi * t / 2.0  # 2s loop
    amp = (0.25 + 0.75 * u)
    disp = amp * (26 * np.sin(u * 7.0 - ph + v * 1.3) + 11 * np.sin(u * 13.0 - 2 * ph + v * 2.1))
    shade = 1 + 0.16 * amp * np.cos(u * 7.0 - ph + v * 1.3) + 0.07 * amp * np.cos(u * 13.0 - 2 * ph + v * 2.1)
    vv = fy_ - disp
    edge = np.clip((vv - FH * 0.5) / 2.5 + 0.5, 0, 1)[..., None]
    white = np.array([238, 238, 240], np.float32); red = np.array(RED, np.float32)
    col = white * (1 - edge) + red * edge
    col = col * shade[..., None]
    return Image.fromarray(np.clip(col, 0, 255).astype(np.uint8), 'RGB').resize((W, H), Image.BILINEAR)

# static darkening overlay
def make_overlay():
    y = np.linspace(0, 1, H)[:, None]
    x = np.linspace(-1, 1, W)[None, :]
    a = 0.40 + 0.14 * (x ** 2)
    a = a + 0.22 * np.exp(-((y - 0.165) / 0.09) ** 2) + 0.16 * np.exp(-((y - 0.84) / 0.07) ** 2)
    a = np.clip(a, 0, 0.93)
    ov = np.zeros((H, W, 4), np.uint8)
    ov[..., 0] = 6; ov[..., 1] = 8; ov[..., 2] = 14
    ov[..., 3] = (a * 255).astype(np.uint8)
    return Image.fromarray(ov, 'RGBA')
OVERLAY = make_overlay()

# ---------- text helpers ----------
def text_c(d, xy, txt, font, fill, anchor='mm', shadow=True, spacing=6):
    if shadow:
        d.multiline_text((xy[0] + 3, xy[1] + 4), txt, font=font, fill=(0, 0, 0, int(fill[3] * 0.55) if len(fill) == 4 else 140), anchor=anchor, align='center', spacing=spacing)
    d.multiline_text(xy, txt, font=font, fill=fill, anchor=anchor, align='center', spacing=spacing)

def with_a(c, a): return tuple(c[:3]) + (int(255 * max(0, min(1, a))),)

def draw_sub(img, cap, a, rise):
    d = ImageDraw.Draw(img)
    words = cap.split(' ')
    lines, cur = [], []
    for w_ in words:
        test = ' '.join(cur + [w_])
        if d.textlength(test, font=F_SUB) > 900 and cur:
            lines.append(cur); cur = [w_]
        else:
            cur.append(w_)
    lines.append(cur)
    lh = 66
    total_h = lh * len(lines)
    y0 = 1615 - total_h / 2 + (1 - rise) * 18
    maxw = max(d.textlength(' '.join(l), font=F_SUB) for l in lines)
    box = Image.new('RGBA', img.size, (0, 0, 0, 0))
    bd = ImageDraw.Draw(box)
    bd.rounded_rectangle((W / 2 - maxw / 2 - 30, y0 - 18, W / 2 + maxw / 2 + 30, y0 + total_h + 14), 22, fill=(8, 10, 16, int(170 * a)))
    bd.rectangle((W / 2 - maxw / 2 - 30, y0 - 18, W / 2 - maxw / 2 - 22, y0 + total_h + 14), fill=with_a(RED, a))
    img.alpha_composite(box)
    d = ImageDraw.Draw(img)
    for li, l in enumerate(lines):
        lw = d.textlength(' '.join(l), font=F_SUB)
        x = W / 2 - lw / 2; y = y0 + li * lh
        for w_ in l:
            col = RED_HI if re.search(r'\d{3,4}', w_) else (255, 255, 255)
            d.text((x + 2, y + 3), w_, font=F_SUB, fill=(0, 0, 0, int(120 * a)))
            d.text((x, y), w_, font=F_SUB, fill=with_a(col, a))
            x += d.textlength(w_ + ' ', font=F_SUB)

def draw_timeline(d, t, si):
    key = TL[si]['key']
    n = len(YEARS); x0, x1, y = 80, 1000, 1468
    xs = [x0 + (x1 - x0) * i / (n - 1) for i in range(n)]
    cur = None
    sc = SC[key]
    if sc['year']: cur = YEARS.index(sc['year'])
    elif key == 'outro': cur = n - 1
    vis = 1.0 if key != 'intro' else ease((t - 6.5) / 1.5)
    if vis <= 0: return
    d.line((x0, y, x1, y), fill=(255, 255, 255, int(70 * vis)), width=3)
    if cur is not None:
        st = TL[si]['start']
        a = ease((t - st) / 0.9)
        px = xs[max(0, cur - 1)] + (xs[cur] - xs[max(0, cur - 1)]) * a if cur > 0 else xs[0]
        d.line((x0, y, px, y), fill=with_a(RED, vis), width=5)
    for i, x in enumerate(xs):
        on = cur is not None and i <= cur
        r = 11 if i == cur else 6
        d.ellipse((x - r, y - r, x + r, y + r), fill=with_a(RED if on else (110, 116, 130), vis), outline=with_a((255, 255, 255), vis * (1 if i == cur else 0.25)), width=3 if i == cur else 1)
        f = F_TLB if i == cur else F_TL
        d.text((x, y + 32), str(YEARS[i]), font=f, fill=with_a((255, 255, 255) if i == cur else (170, 176, 190), vis), anchor='mm')

def draw_arrow(d, p0, p1, prog, a):
    if prog <= 0: return
    pts = []
    mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2 - 70
    for i in range(41):
        s = i / 40 * prog
        x = (1 - s) ** 2 * p0[0] + 2 * (1 - s) * s * mx + s * s * p1[0]
        y = (1 - s) ** 2 * p0[1] + 2 * (1 - s) * s * my + s * s * p1[1]
        pts.append((x, y))
    d.line(pts, fill=with_a((255, 255, 255), a), width=7, joint='curve')
    (xa, ya), (xb, yb) = pts[-2], pts[-1]
    ang = math.atan2(yb - ya, xb - xa)
    L = 30
    h1 = (xb - L * math.cos(ang - 0.5), yb - L * math.sin(ang - 0.5))
    h2 = (xb - L * math.cos(ang + 0.5), yb - L * math.sin(ang + 0.5))
    d.polygon([(xb + 6 * math.cos(ang), yb + 6 * math.sin(ang)), h1, h2], fill=with_a((255, 255, 255), a))

def year_at(t, si):
    s = TL[si]; sc = SC[s['key']]
    if not sc['year']: return None
    prev = SC[TL[si - 1]['key']]['year'] or sc['year'] - 30
    a = ease_out((t - s['start']) / 1.0)
    return int(round(prev + (sc['year'] - prev) * a))

# ---------- frame ----------
def frame(n):
    t = n / FPS
    img = flag(t).convert('RGBA')
    img.alpha_composite(OVERLAY)
    cam, si = camera(t)
    s = TL[si]; key = s['key']; sc = SC[key]
    # map with crossfade
    XF = 0.7
    m, view = crop_map(key, cam)
    if si > 0 and t - s['start'] < XF:
        pm, _ = crop_map(TL[si - 1]['key'], cam)
        m = Image.blend(pm, m, ease((t - s['start']) / XF))
    arr = np.asarray(m).copy()
    mapa = 1.0
    if key == 'intro': mapa = ease((t - 0.2) / 1.6)
    arr[..., 3] = (arr[..., 3] * FEATHER * mapa).astype(np.uint8)
    img.alpha_composite(Image.fromarray(arr, 'RGBA'), (0, MAP_Y0))
    d = ImageDraw.Draw(img)
    # map labels
    lt = t - s['start']
    la = ease((lt - 0.7) / 0.5) * ease((s['end'] - t) / 0.3)
    meta = META['scenes'][key]
    if 'arrow' in meta:
        p0 = to_screen(meta['arrow'][0], view); p1 = to_screen(meta['arrow'][1], view)
        draw_arrow(d, (p0[0] - 10, p0[1]), (p1[0] + 55, p1[1] - 10), ease((lt - 0.9) / 1.4), la)
    for lab in meta['labels']:
        x, y = to_screen(lab['xy'], view)
        y += lab.get('dy', 0)
        text_c(d, (x, y), lab['text'], LABEL_FONTS[lab['size']], with_a((255, 255, 255), la))
    # header
    ka = 1.0 if key != 'intro' else ease((t - 0.4) / 0.8)
    d.text((W / 2, 128), 'H I S T O R I A   P O L S K I', font=F_KICK, fill=with_a((255, 255, 255), 0.85 * ka), anchor='mm')
    d.rectangle((W / 2 - 40, 154, W / 2 + 40, 158), fill=with_a(RED, ka))
    if key == 'intro':
        a = ease((t - 0.6) / 0.9) * ease((s['end'] - t) / 0.5)
        sc_ = 0.92 + 0.08 * ease_out((t - 0.6) / 1.2)
        text_c(d, (W / 2, 300 + (1 - sc_) * 200), 'GRANICE\nPOLSKI', F_BIG, with_a((255, 255, 255), a), spacing=0)
        text_c(d, (W / 2, 452), 'Tysiąc lat zmian na mapie', F_TITLE, with_a((255, 210, 216), a * ease((t - 1.3) / 0.8)))
    elif key == 'outro':
        a = ease((t - s['start'] - 0.6) / 1.0)
        text_c(d, (W / 2, 300), 'POLSKA\nPRZETRWAŁA', F_BIG, with_a((255, 255, 255), a), spacing=0)
        text_c(d, (W / 2, 452), '966 – dziś', F_TITLE, with_a((255, 210, 216), a * ease((t - s['start'] - 1.4) / 0.8)))
    else:
        y = year_at(t, si)
        ya = ease((t - s['start']) / 0.4) * ease((s['end'] - t) / 0.25) if True else 1
        ya = max(ya, 0.0)
        if si > 0 and SC[TL[si - 1]['key']]['year']: ya = 1.0  # keep year visible across scenes (counter rolls)
        text_c(d, (W / 2, 300), str(y), F_YEAR, with_a((255, 255, 255), ya))
        ta = ease((lt - 0.35) / 0.5) * ease((s['end'] - t) / 0.3)
        tw = d.textlength(sc['title'].upper(), font=F_TITLE)
        off = (1 - ease_out((lt - 0.35) / 0.6)) * 30
        bx = Image.new('RGBA', img.size, (0, 0, 0, 0)); bd = ImageDraw.Draw(bx)
        bd.rounded_rectangle((W / 2 - tw / 2 - 26, 414 + off, W / 2 + tw / 2 + 26, 482 + off), 12, fill=with_a(RED, ta * 0.95))
        img.alpha_composite(bx); d = ImageDraw.Draw(img)
        d.text((W / 2, 449 + off), sc['title'].upper(), font=F_TITLE, fill=with_a((255, 255, 255), ta), anchor='mm')
    draw_timeline(d, t, si)
    # subtitles
    for ln in s['lines']:
        if ln['start'] - 0.15 <= t <= ln['end'] + 0.25:
            a = ease((t - ln['start'] + 0.15) / 0.18) * ease((ln['end'] + 0.25 - t) / 0.15)
            draw_sub(img, ln['cap'], a, ease_out((t - ln['start'] + 0.15) / 0.3))
    # global fade in/out
    if t < 0.5 or t > TOTAL - 0.8:
        k = min(ease(t / 0.5), ease((TOTAL - t) / 0.8))
        img = Image.blend(Image.new('RGBA', img.size, (0, 0, 0, 255)), img, k)
    return img.convert('RGB')

def render_range(args):
    a, b, out = args
    p = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                          '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-pix_fmt', 'yuv420p', out], stdin=subprocess.PIPE)
    for n in range(a, b):
        p.stdin.write(frame(n).tobytes())
    p.stdin.close(); p.wait()
    return out

if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'still':
        os.makedirs(f'{S}/stills', exist_ok=True)
        for ts in sys.argv[2:]:
            frame(int(float(ts) * FPS)).save(f'{S}/stills/f_{ts}.jpg', quality=88)
    else:
        from multiprocessing import Pool
        N = 4; os.makedirs(f'{S}/seg', exist_ok=True)
        bounds = [NFRAMES * i // N for i in range(N + 1)]
        jobs = [(bounds[i], bounds[i + 1], f'{S}/seg/s{i}.mp4') for i in range(N)]
        with Pool(N) as pool: segs = pool.map(render_range, jobs)
        with open(f'{S}/seg/list.txt', 'w') as f:
            for sg in segs: f.write(f"file '{sg}'\n")
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', f'{S}/seg/list.txt', '-c', 'copy', f'{S}/video_noaudio.mp4'], check=True)
        print('frames', NFRAMES)
