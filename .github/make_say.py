# «Горько»: find a spelling the male voice stresses on the first syllable (ГО-рько), measured on the two vowels
import os, json, subprocess, asyncio, re, unicodedata, wave
import numpy as np, edge_tts, parselmouth
from faster_whisper import WhisperModel
os.makedirs('out/audio', exist_ok=True); os.makedirs('w', exist_ok=True)
asr = WhisperModel('medium', device='cpu', compute_type='int8')
V = [('ru-RU-DmitryNeural', t) for t in ['Горько!', 'Горька!', 'Гóрько!', 'Го-орько!', 'Гооорько!', 'Горько. ', 'ГОрько!', 'Горь-ко!', 'Горько, горько!', 'Ну, горько!', 'Горько-горько!', 'Гóрька!', 'Го́рько']] + \
    [('ru-RU-SvetlanaNeural', t) for t in ['Горько!']]
async def synth(text, voice, path): await edge_tts.Communicate(text, voice, rate='-12%').save(path)
def vowels(wav):
    snd = parselmouth.Sound(wav)
    it = snd.to_intensity(time_step=0.005); iv = it.values[0]; t = it.xs()
    pt = snd.to_pitch(time_step=0.005, pitch_floor=70, pitch_ceiling=400)
    voiced = np.array([pt.get_value_at_time(x) or 0 for x in t]) > 0
    thr = iv.max() - 12
    on = voiced & (iv > thr)
    segs = []; s = None
    for k, v in enumerate(on):
        if v and s is None: s = k
        if (not v or k == len(on) - 1) and s is not None:
            e = k; 
            if t[e] - t[s] > 0.03: segs.append((t[s], t[e], float(iv[s:e].max()), float(np.nanmedian([pt.get_value_at_time(x) or np.nan for x in t[s:e]]))))
            s = None
    return [(round(a, 2), round(b - a, 3), round(i, 1), round(f, 0) if f == f else None) for a, b, i, f in segs]
rep = []
for k, (voice, txt) in enumerate(V):
    p = 'w/%02d.mp3' % k
    try: asyncio.run(synth(txt, voice, p))
    except Exception as e:
        print(k, txt, 'SKIP', type(e).__name__); continue
    wv = p + '.wav'; subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', p, '-ac', '1', '-ar', '16000', '-acodec', 'pcm_s16le', wv], check=True)
    with wave.open(wv) as w: pcm = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    heard = ' '.join(s.text for s in asr.transcribe(pcm, language='ru', beam_size=5)[0]).strip()
    vs = vowels(wv)
    row = {'k': k, 'voice': voice, 'text': txt, 'heard': heard, 'vowels': vs}
    print(json.dumps(row, ensure_ascii=False)); rep.append(row)
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', p, '-af', 'silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.08,areverse,silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.15,areverse,loudnorm=I=-16:TP=-1.5', '-ac', '1', '-ar', '24000', '-b:a', '48k', 'out/audio/g%02d.mp3' % k], check=True)
json.dump(rep, open('out/report.json', 'w'), ensure_ascii=False, indent=1)
