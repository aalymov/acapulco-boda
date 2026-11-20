import os, json, subprocess, asyncio
import numpy as np, librosa, edge_tts
os.makedirs('out', exist_ok=True); os.makedirs('w', exist_ok=True)
PAIRS = [
 ('es-MX-DaliaNeural', '¿Bailamos?', 'Bailamos.'),
 ('es-MX-DaliaNeural', '¿Cómo estás?', 'Cómo estás.'),
 ('es-MX-DaliaNeural', '¡Hola! ¿Cómo estás?', 'Hola. Cómo estás.'),
 ('ru-RU-SvetlanaNeural', 'Потанцуем?', 'Потанцуем.'),
 ('ru-RU-SvetlanaNeural', 'Как дела?', 'Как дела.'),
 ('ru-RU-SvetlanaNeural', 'Привет! Как дела?', 'Привет. Как дела.'),
]
async def synth(text, voice, path): await edge_tts.Communicate(text, voice, rate='-12%').save(path)
def f0(path):
    y, sr = librosa.load(path, sr=16000)
    f, vf, vp = librosa.pyin(y, fmin=140, fmax=480, sr=sr, frame_length=1024, hop_length=160)
    t = np.arange(len(f)) * 160 / sr
    ok = ~np.isnan(f) & (vp > 0.5)
    return t[ok], 12 * np.log2(f[ok] / 100.0), len(y) / sr
def onset(path):
    y, sr = librosa.load(path, sr=16000)
    e = librosa.feature.rms(y=y, frame_length=320, hop_length=160)[0]
    i = int(np.argmax(e > e.max() * 0.08)); seg = y[i * 160: i * 160 + 1600]
    zcr = float(np.mean(librosa.feature.zero_crossing_rate(seg, frame_length=320, hop_length=160)))
    return round(zcr, 3)
rep = []
for k, (voice, q, s) in enumerate(PAIRS):
    row = {'voice': voice, 'q': q, 's': s}
    for tag, text in (('q', q), ('s', s)):
        p = 'w/%d-%s.mp3' % (k, tag); asyncio.run(synth(text, voice, p))
        t, st, dur = f0(p)
        last = st[t > t.max() - 0.25] if len(t) else []
        row[tag] = {'dur': round(dur, 2), 'end_st': round(float(np.median(last)), 1) if len(last) else None, 'max_last_half_st': round(float(st[t > t.max() / 2].max()), 1) if len(t) else None, 'median_st': round(float(np.median(st)), 1) if len(t) else None,
                    'contour': [round(float(np.median(st[(t >= t.max() * j / 10) & (t < t.max() * (j + 1) / 10)])), 1) if np.any((t >= t.max() * j / 10) & (t < t.max() * (j + 1) / 10)) else None for j in range(10)]}
        subprocess.run(['cp', p, 'out/%d-%s.mp3' % (k, tag)])
    rep.append(row); print(json.dumps(row, ensure_ascii=False))
# the start of "¡Hola!" in the chosen voice: a clean vowel start has a low zero-crossing rate, a "t/k" burst a high one
for voice in ('es-MX-DaliaNeural',):
    p = 'w/hola.mp3'; asyncio.run(synth('¡Hola! ¿Cómo estás?', voice, p)); rep.append({'hola_onset_zcr': onset(p)})
    p = 'w/tola.mp3'; asyncio.run(synth('¡Tola! ¿Cómo estás?', voice, p)); rep.append({'tola_onset_zcr': onset(p)})
print(rep[-2:])
json.dump(rep, open('out/report.json', 'w'), ensure_ascii=False, indent=1)
