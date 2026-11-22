import json, os, urllib.request, urllib.parse, time, io
from PIL import Image
UA = {'User-Agent': 'acapulco-boda-photo-picker/1.0 (wedding site; github.com/aalymov/acapulco-boda)'}
Q = {
 'honeymoon': ['honeymoon beach sunset', 'tropical beach sunset couple', 'couple walking beach sunset', 'overwater bungalow', 'tropical beach hammock'],
 'car': ['car coastal road', 'car road trip sunset', 'new car keys', 'car mountain road', 'convertible road trip'],
 'house': ['cozy house garden', 'house exterior garden', 'modern house exterior', 'house keys new home', 'family home porch'],
}
OK_LIC = {'by', 'by-sa', 'cc0', 'pdm'}
def get(u):
    for i in range(3):
        try: return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=40).read()
        except Exception: time.sleep(3)
    return None
os.makedirs('out/img', exist_ok=True); meta = {}
for theme, qs in Q.items():
    seen, items = set(), []
    for q in qs:
        b = get('https://api.openverse.org/v1/images/?' + urllib.parse.urlencode({'q': q, 'page_size': 12, 'mature': 'false'}))
        if not b: continue
        for r in json.loads(b).get('results', []):
            if r['id'] in seen or r.get('license') not in OK_LIC: continue
            if (r.get('width') or 0) and r['width'] < 900: continue
            seen.add(r['id'])
            items.append({'title': (r.get('title') or '')[:80], 'url': r.get('url'), 'creator': (r.get('creator') or '')[:60], 'license': ('CC0' if r['license'] == 'cc0' else 'PD' if r['license'] == 'pdm' else 'CC ' + r['license'].upper() + ' ' + (r.get('license_version') or '')).strip(), 'page': r.get('foreign_landing_url'), 'q': q})
        time.sleep(1)
    keep = []
    for it in items[:30]:
        data = get(it['url']) if it.get('url') else None
        try:
            im = Image.open(io.BytesIO(data)).convert('RGB')
            if im.width < 800: raise Exception('small')
            if im.width > 1200: im = im.resize((1200, int(im.height * 1200 / im.width)))
            fn = 'img/%s-%02d.jpg' % (theme, len(keep)); im.save('out/' + fn, quality=82); it['local'] = fn; keep.append(it)
        except Exception: pass
    meta[theme] = keep; print(theme, len(items), len(keep))
json.dump(meta, open('out/meta.json', 'w'), ensure_ascii=False, indent=1)
