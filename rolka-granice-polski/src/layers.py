import os, sys, json
sys.path.insert(0, os.path.dirname(__file__))
from geo import load, get, proj
from scenes import SCENES
from shapely.geometry import Polygon, LineString
from shapely.ops import unary_union, split
from PIL import Image, ImageDraw, ImageFilter, ImageChops
S='/tmp/claude-0/-home-user-Xxx/30a8b2ec-cf16-5359-8239-efaca9b7059f/scratchpad'
OUT=f'{S}/layers'; os.makedirs(OUT, exist_ok=True)
X0, X1, Y0, Y1, KM = -2700, 2300, -1700, 2000, 1.6
W, H = int((X1-X0)/KM), int((Y1-Y0)/KM)
def P(x, y): return ((x-X0)/KM, (Y1-y)/KM)
def polys(g):
    if g is None or g.is_empty: return []
    if g.geom_type == 'Polygon': return [g]
    out = []
    for gg in getattr(g, 'geoms', []): out += polys(gg)
    return out
def fill(d, g, color, outline=None, width=1):
    for p in polys(g):
        pts = [P(*c) for c in p.exterior.coords]
        if len(pts) < 3: continue
        d.polygon(pts, fill=color)
        if outline: d.line(pts + [pts[0]], fill=outline, width=width, joint='curve')
def mask_of(g, blur=0):
    m = Image.new('L', (W, H), 0); fill(ImageDraw.Draw(m), g, 255)
    return m.filter(ImageFilter.GaussianBlur(blur)) if blur else m
RED = (220, 20, 60)
SEA = (10, 17, 30, 205)
LAND = (38, 45, 60, 250)
BORD = (88, 99, 120, 255)
def lp(g):
    c = g.representative_point() if g.geom_type != 'Polygon' else g.representative_point()
    # prefer centroid if inside
    ce = g.centroid
    return [ce.x, ce.y] if g.contains(ce) else [c.x, c.y]
def poland_layer(img, g, alpha=255):
    glow = mask_of(g, 22).point(lambda v: int(v*0.85))
    gl = Image.new('RGBA', (W, H), RED + (0,)); gl.putalpha(glow)
    img.alpha_composite(gl)
    lay = Image.new('RGBA', (W, H), (0,0,0,0)); d = ImageDraw.Draw(lay)
    fill(d, g, RED + (alpha,), outline=(255, 235, 238, 255), width=3)
    img.alpha_composite(lay)
def line39():
    pts = [(23.6,55.5),(23.0,54.3),(22.6,53.6),(22.3,53.1),(22.0,52.75),(22.9,52.4),(23.4,52.2),(23.7,51.6),(24.1,50.9),(23.7,50.4),(22.9,50.0),(22.6,49.5),(22.7,48.6)]
    xy = [proj(*p) for p in pts]
    east = xy + [proj(40, 46), proj(40, 60)]
    return Polygon(east)
meta = {}
for sc in SCENES:
    yr = sc['geo']
    img = Image.new('RGBA', (W, H), SEA); d = ImageDraw.Draw(img)
    for n, g in load(yr): fill(d, g, LAND)
    for n, g in load(yr): fill(d, g, None if False else LAND, outline=BORD, width=2)
    m = {'labels': []}
    ghost = sc.get('ghost')
    if ghost:
        gg = get(*ghost)
        lay = Image.new('RGBA', (W, H), (0,0,0,0)); dl = ImageDraw.Draw(lay)
        fill(dl, gg, (150, 25, 45, 150), outline=(255, 160, 170, 200), width=3)
        img.alpha_composite(lay)
        m['ghost_c'] = lp(gg)
    if sc.get('partition'):
        plc = get(1700, ['Polish–Lithuanian Commonwealth'])
        cols = {'Prussia': ((70, 105, 160), 'PRUSY'), 'Austrian Empire': ((190, 150, 45), 'AUSTRIA'), 'Russian Empire': ((95, 130, 85), 'ROSJA')}
        lay = Image.new('RGBA', (W, H), (0,0,0,0)); dl = ImageDraw.Draw(lay)
        for nm, (c, lab) in cols.items():
            part = get(1800, [nm]).intersection(plc)
            fill(dl, part, c + (235,), outline=(20, 25, 35, 255), width=2)
            big = max(polys(part), key=lambda p: p.area)
            m['labels'].append({'xy': lp(big), 'text': lab, 'size': 38})
        fill(dl, plc, None, outline=RED + (255,), width=6)
        img.alpha_composite(lay)
    elif sc.get('split39'):
        pl = get(yr, sc['names'])
        east = pl.intersection(line39()); west = pl.difference(line39())
        poland_layer(img, pl, 0)
        lay = Image.new('RGBA', (W, H), (0,0,0,0)); dl = ImageDraw.Draw(lay)
        fill(dl, west, (85, 90, 102, 250)); fill(dl, east, (120, 50, 42, 250))
        fill(dl, pl, None, outline=RED + (255,), width=6)
        img.alpha_composite(lay)
        m['labels'] += [{'xy': lp(west), 'text': 'III RZESZA', 'size': 36}, {'xy': lp(east), 'text': 'ZSRR', 'size': 36}]
        m['poland_c'] = lp(pl)
    else:
        pl = get(yr, sc['names'])
        poland_layer(img, pl)
        m['poland_c'] = lp(max(polys(pl), key=lambda p: p.area))
        if sc.get('arrow'):
            g38 = get(*sc['ghost'])
            kresy = max(polys(g38.difference(pl)), key=lambda p: p.area)
            west = max(polys(pl.difference(g38)), key=lambda p: p.area)
            m['arrow'] = [lp(kresy), lp(west)]
            m['labels'] += [{'xy': lp(kresy), 'text': 'KRESY', 'size': 34, 'dy': -50}, {'xy': lp(west), 'text': 'ZIEMIE\nZACHODNIE', 'size': 34, 'dy': 105}]
        elif sc.get('label'): m['labels'].append({'xy': m['poland_c'], 'text': sc['label'], 'size': 34})
        b = pl.bounds; m['bounds'] = b
    img.save(f"{OUT}/{sc['key']}.png", compress_level=1)
    meta[sc['key']] = m
    print(sc['key'], m)
json.dump({'X0': X0, 'Y1': Y1, 'KM': KM, 'W': W, 'H': H, 'scenes': meta}, open(f'{OUT}/meta.json', 'w'), indent=1)
