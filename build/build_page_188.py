"""build_page_188.py — turns data/ into index.html from build/laf_template.html. Same shape as the Mott build.
Run: python3 build/build_page.py   (then build/make_card.sh for og.jpg)"""
import json, os, base64, datetime, collections, re, math
S = os.path.dirname(os.path.abspath(__file__)); R = os.path.dirname(S); D = os.path.join(R, 'data')
LAT, LON = 40.7209251, -73.9985317
TODAY = datetime.date(2026, 10, 8)
NEAR = ('409', '623')                # Spring St 6 192 m, Canal St 273 m: the two inside 300 m
ALLCX = ('409', '623', '17', '619')  # plus Prince St 383 m, Broadway-Lafayette 522 m
NAMES = {'409': 'Spring St · 6', '623': 'Canal St · 6 J N Q R W Z', '17': 'Prince St · R W', '619': 'Broadway-Lafayette · B D F M'}
def J(n):
    p = os.path.join(D, n)
    if not os.path.exists(p) or os.path.getsize(p) < 3: return None
    r = json.load(open(p)); return None if isinstance(r, dict) else r
def dist(lat, lon): return math.hypot((lon - LON) * 111320 * math.cos(math.radians(LAT)), (lat - LAT) * 110540)
days = collections.Counter(); d = datetime.date(2026, 6, 1)
while d <= datetime.date(2026, 8, 31): days[(d.weekday() + 1) % 7] += 1; d += datetime.timedelta(days=1)

# ---- subway: hour x weekday per complex, summer 2026 ----
hourly = {}
for cx in ALLCX:
    h = {dw: [0.0] * 24 for dw in range(7)}
    for x in (J(f'mta_hourly_{cx}.json') or []): h[int(x['dow'])][int(x['hr'])] = float(x['riders']) / days[int(x['dow'])]
    hourly[cx] = h
l_hourly = {dw: [round(sum(hourly[cx][dw][h] for cx in NEAR), 1) for h in range(24)] for dw in range(7)}
wkd = lambda h: [sum(h[d][hr] for d in (1, 2, 3, 4, 5)) / 5 for hr in range(24)]
wk = wkd(l_hourly); cxday = {cx: round(sum(wkd(hourly[cx]))) for cx in ALLCX}
peak_hr = max(range(24), key=lambda h: wk[h])
hl = lambda h: f"{(h + 11) % 12 + 1} {'am' if h < 12 else 'pm'}"

# ---- bus: stops within 300 m ----
def parse_hour(s):
    m = re.search(r'(\d{1,2}):\d{2}:\d{2}\s*(AM|PM)', s, re.I)
    if m: return int(m.group(1)) % 12 + (12 if m.group(2).upper() == 'PM' else 0)
    m = re.search(r'T(\d{2}):', s)
    if m: return int(m.group(1))
    return int(s) if s.strip().isdigit() else None
stops = [s['stop_id'] for s in (J('bus_stops_near.json') or []) if s['d'] <= 300]
bus = {dw: [0.0] * 24 for dw in range(7)}
for r in (J('bus_raw.json') or []):
    dt = datetime.date.fromisoformat(r['date'][:10]); dw = (dt.weekday() + 1) % 7; h = parse_hour(str(r.get('hour', '')))
    if h is None or r['stop_id'] not in stops: continue
    bus[dw][h] += float(r.get('boardings') or 0) + float(r.get('alightings') or 0)
for dw in bus: bus[dw] = [round(v / days[dw], 2) for v in bus[dw]]
bus_day = round(sum(sum(bus[d][h] for d in (1, 2, 3, 4, 5)) / 5 for h in range(24)))
mon = collections.defaultdict(float)
for r in (J('bus_monthly.json') or []):
    if r['stop_id'] in stops: mon[r['month'][:7]] += float(r['b']) + float(r['a'])
ms = sorted(mon.items()); bus_month = round(sum(v for _, v in ms[-13:-1]) / max(1, len(ms[-13:-1])))

# ---- cars: the nearest DOT counter is Spring St eastbound, Crosby to Cleveland Place, one block north, 2015 ----
byday = collections.defaultdict(lambda: [0.0] * 24); slots = collections.Counter()
for r in (J('atr.json') or []):
    if r['street'].upper() == 'SPRING STREET' and 'CROSBY' in r.get('fromst', '').upper():
        k = (r['yr'], r['m'], r['d']); byday[k][int(r['hh'])] += float(r['vol']); slots[k] += 1
full = [v for k, v in byday.items() if slots[k] >= 96]
car_hourly = [round(sum(v[h] for v in full) / len(full)) for h in range(24)] if full else [0] * 24
car_day = sum(car_hourly)
json.dump({'street': 'Spring St, Crosby to Cleveland Place, eastbound', 'when': '2015', 'full_days': len(full), 'per_day': car_day, 'hourly': car_hourly}, open(os.path.join(D, 'atr_summary.json'), 'w'))

# ---- the years ----
def months_from(cx):
    out = {}
    for r in (J(f'mta_hist_{cx}.json') or []): out[r['month'][:7]] = out.get(r['month'][:7], 0) + float(r['riders'])
    return sorted([[m, v] for m, v in out.items() if m <= '2026-08'])
series = []; ratios = {}
for cx, col in zip(ALLCX, ('f', 'c', 'jz', 'bd')):
    pts = months_from(cx); m = dict(pts); ratios[cx] = round(m.get('2026-08', 0) / m.get('2020-01', 1) * 100)
    series.append({'k': col, 'label': NAMES[cx].split(' · ')[0], 'pts': pts})
near_m = collections.defaultdict(float)
for cx in NEAR:
    for m, v in months_from(cx): near_m[m] += v
ratio = round(near_m.get('2026-08', 0) / near_m.get('2020-01', 1) * 100)

# ---- daily against the weather, three stations summed ----
w = json.load(open(os.path.join(D, 'weather.json')))['daily']
wx = {t: (w['temperature_2m_max'][i], w['precipitation_sum'][i] or 0.0, w['snowfall_sum'][i] or 0.0) for i, t in enumerate(w['time'])}
dsum = collections.defaultdict(float)
for cx in NEAR:
    for r in (J(f'mta_daily_{cx}.json') or []): dsum[r['day'][:10]] += float(r['riders'])
daily = [[dt, round(v), round(wx[dt][0], 1), round(wx[dt][1], 2), round(wx[dt][2], 2)] for dt, v in sorted(dsum.items()) if dt in wx and '2025-01-01' <= dt <= '2026-08-31' and wx[dt][0] is not None]

fsum = collections.defaultdict(float)
for cx in NEAR:
    for x in (J(f'fare_{cx}.json') or []): fsum[x['fare_class_category']] += float(x['riders'])
t = sum(fsum.values()) or 1
fare = ' · '.join(f"{k.replace('OMNY - ', '')} {v / t * 100:.0f}%" for k, v in sorted(fsum.items(), key=lambda kv: -kv[1])[:4]) + ' (three stations, summer 2026)'

cams = []; camtime = ''
for c in (J('cameras.json') or [])[:6]:
    fp = os.path.join(R, c['file'])
    if os.path.exists(fp) and os.path.getsize(fp) > 1000:
        cams.append({'name': c['name'], 'dist': c['dist'], 'id': c['id'], 't': c['t'], 'src': 'data:image/jpeg;base64,' + base64.b64encode(open(fp, 'rb').read()).decode()}); camtime = c['t']

# ---- crashes, vacancy ----
cr = [r for r in json.load(open(os.path.join(D, 'raw', 'collisions.json'))) if r.get('latitude') and r['crash_date'] >= '2023-01-01' and dist(float(r['latitude']), float(r['longitude'])) <= 150]
SUM = lambda k: sum(int(r.get(k) or 0) for r in cr)
reg = json.load(open(os.path.join(D, 'raw', 'registry_block.json'))); y24 = {}
for r in reg:
    if r['reporting_year'].startswith('2024'): y24[(r['bbl'], r.get('property_street_address_or'), r.get('primary_business_activity'))] = r
vac_n = sum(1 for r in y24.values() if str(r.get('vacant_on_12_31', '')).upper().startswith('Y')); vac_t = len(y24)

dark_min = dark_max = 0   # no dark-date bracket on this page

nbldg = len(json.load(open(os.path.join(D, 'planimetric', 'footprints.geojson')))['features'])
ntrees = sum(1 for x in json.load(open(os.path.join(D, 'planimetric', 'trees.json'))) if x.get('status') == 'Alive')
points = json.load(open(os.path.join(D, 'model_points.json')))
# the door the page flies to: the pink store, 9 ft south of the Broome corner along Lafayette, in glTF space (x east, z south)
_cos = math.cos(math.radians(LAT)); _p = lambda lo, la: ((lo - LON) * 111320 * _cos, (la - LAT) * 110540)
_c = _p(-73.998395376221, 40.721042374639); _s = _p(-73.998616527288, 40.720779485378); _L = math.dist(_c, _s); _f = 9 * 0.3048 / _L
points['door'] = [round(_c[0] + (_s[0] - _c[0]) * _f, 1), 0, round(-(_c[1] + (_s[1] - _c[1]) * _f), 1)]
killed = SUM('number_of_persons_killed')

data = {'l_hourly': l_hourly, 'bus_a': bus, 'car_hourly': car_hourly, 'series': series, 'daily': daily, 'fare': fare, 'cams': cams}
f = lambda n: f"{n:,}"
subs = {'__DATA__': json.dumps(data, separators=(',', ':')), '__POINTS__': json.dumps(points), '__DARKMIN__': str(dark_min), '__DARKMAX__': str(dark_max), '__TODAY__': f"{TODAY.day} {TODAY:%B %Y}",
        '__CARS__': f(car_day), '__CARPEAK__': f(max(car_hourly)), '__CRASH__': str(len(cr)), '__HURT__': str(SUM('number_of_persons_injured')), '__PED__': str(SUM('number_of_pedestrians_injured')), '__CYC__': str(SUM('number_of_cyclist_injured')),
        '__KILLED__': 'none killed' if not killed else f"{killed} killed",
        '__SUBDAY__': f(round(sum(wk))), '__SUBPEAK__': f(round(max(wk))), '__SUBPEAKHR__': hl(peak_hr), '__SUB8__': f(round(wk[8])), '__RATIO__': str(ratio),
        '__S409__': f(cxday['409']), '__S623__': f(cxday['623']), '__S17__': f(cxday['17']), '__S619__': f(cxday['619']),
        '__R409__': str(ratios['409']), '__R623__': str(ratios['623']), '__R17__': str(ratios['17']), '__R619__': str(ratios['619']),
        '__VACN__': str(vac_n), '__VACT__': str(vac_t), '__VACPCT__': str(round(vac_n / max(1, vac_t) * 100)),
        '__BUSDAY__': f(bus_day), '__BUSMO__': f(bus_month), '__CAMTIME__': camtime, '__NBLDG__': f(nbldg), '__NTREES__': f(ntrees)}
out = open(os.path.join(S, 'laf_template.html')).read()
for k, v in subs.items(): out = out.replace(k, v)
left = sorted(set(re.findall(r'__[A-Z0-9]+__', out)))
open(os.path.join(R, 'index.html'), 'w').write(out)
print({k: v for k, v in subs.items() if k not in ('__DATA__', '__POINTS__')})
print(f"built index.html {len(out) // 1024} KB · cams {len(cams)} · daily {len(daily)} · bus stops {stops} · car full days {len(full)} · unfilled {left}")
