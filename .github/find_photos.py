import json, os, urllib.request, urllib.parse, re, time, io
from PIL import Image
UA = {'User-Agent': 'acapulco-boda-photo-picker/1.0 (wedding site; github.com/aalymov/acapulco-boda)'}
Q = {
 'ru-vykup': ['russian wedding ransom', 'выкуп невесты', 'russian wedding bridesmaids groom', 'ukrainian wedding ransom bride', 'russian wedding groom door'],
 'ru-tamada': ['wedding toastmaster', 'wedding mc microphone', 'wedding host microphone guests', 'russian wedding host', 'тамада свадьба'],
 'mx-padrinos': ['padrinos boda', 'mexican wedding padrinos', 'mexican wedding church', 'boda mexicana iglesia', 'filipino wedding sponsors'],
 'mx-vibora': ['vibora de la mar', 'mexican wedding vibora', 'wedding conga line', 'bride groom chairs dance', 'mexican wedding dance'],
 'mx-batucada': ['batucada boda', 'batucada', 'hora loca boda', 'samba drummers', 'wedding drummers'],
 'mx-altar': ['bride walking down the aisle', 'mexican wedding bride church', 'bride entering church', 'boda novia iglesia', 'groom waiting bride altar'],
}
OK_LIC = {'by', 'by-sa', 'cc0', 'pdm', 'by-nc', 'by-nc-sa'}
def get(u):
    for i in range(3):
        try: return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=40).read()
        except Exception: time.sleep(3)
    return None
os.makedirs('out/img', exist_ok=True)
meta = {}
for theme, qs in Q.items():
    seen, items = set(), []
    for q in qs:
        b = get('https://api.openverse.org/v1/images/?' + urllib.parse.urlencode({'q': q, 'page_size': 20, 'mature': 'false'}))
        if not b: continue
        for r in json.loads(b).get('results', []):
            if r['id'] in seen or r.get('license') not in OK_LIC: continue
            if (r.get('width') or 0) and r['width'] < 700: continue
            seen.add(r['id'])
            items.append({'id': r['id'], 'title': (r.get('title') or '')[:80], 'url': r.get('url'), 'thumb': r.get('thumbnail'), 'creator': (r.get('creator') or '')[:60], 'license': ('CC0' if r['license'] == 'cc0' else 'PD' if r['license'] == 'pdm' else 'CC ' + r['license'].upper() + ' ' + (r.get('license_version') or '')).strip(), 'page': r.get('foreign_landing_url'), 'src': r.get('source'), 'q': q})
        time.sleep(1)
        if len(items) >= 30: break
    keep = []
    for it in items[:30]:
        data = get(it['url']) if it.get('url') else None
        try:
            im = Image.open(io.BytesIO(data)).convert('RGB')
            if im.width < 600: raise Exception('small')
            if im.width > 900: im = im.resize((900, int(im.height * 900 / im.width)))
            fn = 'img/%s-%02d.jpg' % (theme, len(keep)); im.save('out/' + fn, quality=82); it['local'] = fn; keep.append(it)
        except Exception as e:
            pass
    meta[theme] = keep
    print(theme, len(items), len(keep))
json.dump(meta, open('out/meta.json', 'w'), ensure_ascii=False, indent=1)
