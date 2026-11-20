import os, json, subprocess, asyncio, re, unicodedata, wave
import numpy as np, edge_tts, parselmouth
from faster_whisper import WhisperModel
os.makedirs('out/audio', exist_ok=True); os.makedirs('w', exist_ok=True)
asr = WhisperModel('medium', device='cpu', compute_type='int8')
FINAL = {
 'es': ('es-MX-DaliaNeural', [['¡Hola! ¿Cómo estás?'], ['Mucho gusto.'], ['¡Salud!'], ['¡Que vivan los novios!'], ['¿Bailamos?'], ['¡Está delicioso!'], ['Gracias.']]),
 'ru': ('ru-RU-DmitryNeural', [['Привет! Как дела?'], ['Очень приятно.'], ['За молодых!'], ['Го́рько!', 'Горько!', 'Горько-о!', 'Горька!', 'Гоорько!'], ['Потанцуем??', 'Потанцуем?!'], ['Очень вкусно!'], ['Спасибо.']]),
}
TARGET = {'es': ['Hola cómo estás', 'Mucho gusto', 'Salud', 'Que vivan los novios', 'Bailamos', 'Está delicioso', 'Gracias'],
          'ru': ['Привет как дела', 'Очень приятно', 'За молодых', 'Горько', 'Потанцуем', 'Очень вкусно', 'Спасибо']}
def norm(s):
    s = unicodedata.normalize('NFD', s.lower()); s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-zа-яё ]', '', s.replace('ё', 'е')).split()
def prof(wav):
    snd = parselmouth.Sound(wav); pt = snd.to_pitch(time_step=0.01, pitch_floor=70, pitch_ceiling=450)
    f = pt.selected_array['frequency']; t = pt.xs(); m = f > 0
    if m.sum() < 5: return None
    st = 12 * np.log2(f[m] / 100.0); tv = t[m]; a, b = tv.min(), tv.max()
    return [round(float(np.median(st[(tv >= a + (b - a) * j / 8) & (tv <= a + (b - a) * (j + 1) / 8)])), 1) if np.any((tv >= a + (b - a) * j / 8) & (tv <= a + (b - a) * (j + 1) / 8)) else None for j in range(8)]
async def synth(text, voice, path): await edge_tts.Communicate(text, voice, rate='-12%').save(path)
rep = {}
for lang, (voice, items) in FINAL.items():
    rep[lang] = []
    for i, variants in enumerate(items):
        chosen = None
        for vi, txt in enumerate(variants):
            raw = 'w/%s-%d-%d.mp3' % (lang, i, vi)
            try: asyncio.run(synth(txt, voice, raw))
            except Exception as e:
                print(lang, i, 'SKIP', txt, type(e).__name__); continue
            w16 = raw + '.wav'; subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', raw, '-ac', '1', '-ar', '16000', '-acodec', 'pcm_s16le', w16], check=True)
            with wave.open(w16) as w: pcm = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
            heard = ' '.join(s.text for s in asr.transcribe(pcm, language=lang, beam_size=5)[0]).strip()
            ok = norm(heard) == norm(TARGET[lang][i])
            row = {'i': i, 'text': txt, 'heard': heard, 'ok': ok, 'pitch': prof(w16)}
            print(lang, i, 'OK ' if ok else 'BAD', txt, '->', heard, row['pitch'])
            rep[lang].append(row)
            if ok:
                chosen = raw; break
        if chosen is None: chosen = sorted(f for f in os.listdir('w') if f.startswith('%s-%d-' % (lang, i)) and f.endswith('.mp3'))[0]; chosen = 'w/' + chosen
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', chosen, '-af', 'silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.08,areverse,silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.15,areverse,loudnorm=I=-16:TP=-1.5', '-ac', '1', '-ar', '24000', '-b:a', '48k', 'out/audio/%s-%02d.mp3' % (lang, i)], check=True)
json.dump(rep, open('out/report.json', 'w'), ensure_ascii=False, indent=1)
