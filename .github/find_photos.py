import json, os, urllib.request, urllib.parse, re, time
UA = {'User-Agent': 'acapulco-boda-photo-picker/1.0 (wedding site; github.com/aalymov/acapulco-boda)'}
Q = {
 'mx-padrinos': ['padrinos boda', 'Mexican wedding godparents', 'boda mexicana'],
 'mx-lazo': ['lazo boda', 'wedding lasso ceremony', 'lazo matrimonial'],
 'mx-tornaboda': ['taquiza', 'tacos al pastor', 'chilaquiles'],
 'mx-vibora': ['vibora de la mar', 'wedding guests dancing conga', 'wedding reception dance'],
 'mx-batucada': ['batucada', 'samba drummers', 'batucada drums street'],
 'mx-altar': ['bride walking aisle', 'novia altar boda', 'bride father aisle wedding'],
 'mx-mariachi': ['mariachi', 'mariachi band', 'mariachi trumpet'],
 'mx-liga': ['wedding garter', 'garter toss', 'bride garter'],
 'ru-karavai': ['karavai wedding', 'каравай свадьба', 'korovai bread'],
 'ru-gorko': ['wedding kiss', 'свадьба поцелуй', 'bride groom kiss'],
 'ru-toast': ['wedding toast', 'champagne toast', 'toasting glasses wedding'],
 'ru-vykup': ['выкуп невесты', 'bride ransom', 'свадьба выкуп'],
 'ru-witness': ['свидетели свадьба', 'best man bridesmaid', 'свидетельница лента'],
 'ru-tamada': ['тамада', 'wedding host microphone', 'wedding entertainer'],
 'ru-ring': ['wedding rings hands', 'обручальное кольцо', 'wedding ring hand'],
 'ru-day2': ['wedding feast table', 'russian wedding table', 'свадебный стол'],
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
for theme, qs in Q.items():
    seen, items = set(), []
    for q in qs:
        d = api({'action': 'query', 'format': 'json', 'generator': 'search', 'gsrnamespace': 6, 'gsrsearch': q + ' filetype:bitmap', 'gsrlimit': 10,
                 'prop': 'imageinfo', 'iiprop': 'url|extmetadata|size|mime', 'iiurlwidth': 640})
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
            if len(items) >= 12: break
        if len(items) >= 12: break
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
