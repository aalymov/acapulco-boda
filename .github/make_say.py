import os, json, subprocess, asyncio
import numpy as np, edge_tts, parselmouth
os.makedirs('out', exist_ok=True); os.makedirs('w', exist_ok=True)
async def synth(text, voice, path, rate='-12%', pitch='+0Hz'): await edge_tts.Communicate(text, voice, rate=rate, pitch=pitch).save(path)
def prof(path):
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', path, path + '.wav'], check=True)
    snd = parselmouth.Sound(path + '.wav'); pt = snd.to_pitch(time_step=0.01, pitch_floor=75, pitch_ceiling=500)
    f = pt.selected_array['frequency']; t = pt.xs(); m = f > 0
    if m.sum() < 5: return None
    st = 12 * np.log2(f[m] / 100.0); tv = t[m]; a, b = tv.min(), tv.max()
    bins = [round(float(np.median(st[(tv >= a + (b - a) * j / 8) & (tv <= a + (b - a) * (j + 1) / 8)])), 1) if np.any((tv >= a + (b - a) * j / 8) & (tv <= a + (b - a) * (j + 1) / 8)) else None for j in range(8)]
    return {'bins': bins, 'peak': round(float(st.max()), 1), 'end': round(float(np.median(st[tv > b - 0.12])), 1), 'start': round(float(np.median(st[tv < a + 0.12])), 1)}
TESTS = []
for v in ('ru-RU-SvetlanaNeural', 'ru-RU-DmitryNeural'):
    for txt in ('Потанцуем.', 'Потанцуем?', 'Потанцу́ем?', 'Потанцуем?!', 'Потанцуем??', '— Потанцуем?', 'А потанцуем?', 'Ну что, потанцуем?'):
        TESTS.append((v, txt))
for v in ('es-MX-DaliaNeural',):
    for txt in ('Bailamos.', '¿Bailamos?', 'Hola. Cómo estás.', '¡Hola! ¿Cómo estás?'):
        TESTS.append((v, txt))
for v in ('ru-RU-SvetlanaNeural',):
    for txt in ('Привет. Как дела.', 'Привет! Как дела?', 'Привет! Как дела́?'):
        TESTS.append((v, txt))
rep = []
for k, (v, txt) in enumerate(TESTS):
    p = 'out/%02d.mp3' % k; asyncio.run(synth(txt, v, p)); r = prof(p)
    rep.append({'k': k, 'voice': v, 'text': txt, 'p': r}); print(k, v, txt, r)
json.dump(rep, open('out/report.json', 'w'), ensure_ascii=False, indent=1)
