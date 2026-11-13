import json, math
from shapely.geometry import shape, box
from shapely.ops import unary_union, transform
from shapely.validation import make_valid
DATA = '/tmp/claude-0/-home-user-Xxx/30a8b2ec-cf16-5359-8239-efaca9b7059f/scratchpad/data'
LON0, LAT0 = math.radians(19.0), math.radians(52.0)
def proj(lon, lat):
    l = math.radians(lon); p = math.radians(lat)
    c = 1 + math.sin(LAT0)*math.sin(p) + math.cos(LAT0)*math.cos(p)*math.cos(l-LON0)
    k = math.sqrt(2/c) * 6371.0
    return k*math.cos(p)*math.sin(l-LON0), k*(math.cos(LAT0)*math.sin(p)-math.sin(LAT0)*math.cos(p)*math.cos(l-LON0))
def _pt(x, y, z=None):
    try:
        xs = [proj(a, b) for a, b in zip(x, y)]
        return [p[0] for p in xs], [p[1] for p in xs]
    except TypeError:
        return proj(x, y)
CLIP = box(-30, 25, 60, 75)
_cache = {}
def load(year):
    if year in _cache: return _cache[year]
    d = json.load(open(f'{DATA}/world_{year}.geojson'))
    out = []
    for f in d['features']:
        if not f.get('geometry'): continue
        g = make_valid(shape(f['geometry']))
        g = g.intersection(CLIP)
        if g.is_empty: continue
        g = make_valid(transform(_pt, g)).buffer(0)
        out.append((f['properties'].get('NAME') or '', g))
    _cache[year] = out
    return out
def get(year, names):
    gs = [g for n, g in load(year) if n in names]
    return unary_union(gs) if gs else None
def land(year):
    return unary_union([g for n, g in load(year)])
