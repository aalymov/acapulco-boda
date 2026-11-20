import json, os, urllib.request, urllib.parse, re, time
UA = {'User-Agent': 'acapulco-boda-photo-picker/1.0 (wedding site; github.com/aalymov/acapulco-boda)'}
Q = {
 'ru-vykup': ['выкуп невесты свадьба', 'свадьба подружки невесты', 'russian wedding groom bridesmaids', 'wedding bride ransom game', 'свадьба жених у двери'],
 'ru-tamada': ['wedding MC microphone', 'wedding master of ceremonies', 'свадебный ведущий', 'ведущий свадьбы микрофон', 'wedding host speech microphone', 'wedding emcee'],
 'mx-padrinos': ['padrinos de boda', 'ninong ninang wedding', 'wedding principal sponsors', 'boda iglesia México padrinos', 'wedding godparents'],
 'mx-vibora': ['vibora de la mar boda', 'bride groom standing on chairs', 'wedding conga line', 'wedding guests dance line', 'wedding dance bride lifted'],
 'mx-batucada': ['batucada carnaval', 'batucada noche', 'carnival drummers night', 'samba drummers carnival', 'escola de samba bateria', 'Notting Hill carnival drummers'],
 'mx-altar': ['Wedding Ceremony in Santo Domingo', 'bride walking down the aisle church', 'novia iglesia', 'Kapampangan wedding', 'groom waiting altar', 'boda en la iglesia'],
 'cat-mx': ['cat:Weddings in Mexico'],
 'cat-ru': ['cat:Weddings in Russia'],
}
def api(params):
    u = 'https://commons.wikimedia.org/w/api.php?' + urllib.parse.urlencode(params)
    for i in range(3):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30))
        except Exception as e:
            time.sleep(2)
    return {}
def strip(h): return re.sub(r'<[^>]+>', '', h or '').strip()
os.makedirs('out/img', exist_ok=True)
meta = {}
LIM = 20
for theme, qs in Q.items():
    seen, items = set(), []
    lim = 40 if theme.startswith('cat-') else LIM
    for q in qs:
        base = {'action': 'query', 'format': 'json', 'prop': 'imageinfo', 'iiprop': 'url|extmetadata|size|mime', 'iiurlwidth': 720}
        if q.startswith('cat:'):
            base.update({'generator': 'categorymembers', 'gcmtitle': 'Category:' + q[4:], 'gcmtype': 'file', 'gcmlimit': 50})
        else:
            base.update({'generator': 'search', 'gsrnamespace': 6, 'gsrsearch': q + ' filetype:bitmap', 'gsrlimit': 10})
        d = api(base)
        pages = sorted((d.get('query') or {}).get('pages', {}).values(), key=lambda p: p.get('index', 99))
        for p in pages:
            t = p['title']
            if t in seen: continue
            ii = (p.get('imageinfo') or [{}])[0]
            if ii.get('mime') not in ('image/jpeg',): continue
            if ii.get('width', 0) < 800: continue
            em = ii.get('extmetadata', {})
            lic = strip((em.get('LicenseShortName') or {}).get('value'))
            if not re.search(r'CC|Public domain|PD', lic or '', re.I): continue
            seen.add(t)
            items.append({'file': t[5:], 'thumb': ii.get('thumburl'), 'w': ii.get('width'), 'h': ii.get('height'), 'artist': strip((em.get('Artist') or {}).get('value'))[:80], 'license': lic, 'desc': strip((em.get('ImageDescription') or {}).get('value'))[:160]})
            if len(items) >= lim: break
        if len(items) >= lim: break
    for i, it in enumerate(items):
        fn = 'img/%s-%02d.jpg' % (theme, i)
        try:
            data = urllib.request.urlopen(urllib.request.Request(it['thumb'], headers=UA), timeout=40).read()
            open('out/' + fn, 'wb').write(data); it['local'] = fn
        except Exception as e:
            it['err'] = str(e)
        time.sleep(0.3)
    meta[theme] = items
    print(theme, len(items))
json.dump(meta, open('out/meta.json', 'w'), ensure_ascii=False, indent=1)
