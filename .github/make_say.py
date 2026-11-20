import os, json, wave, subprocess, re, unicodedata, asyncio
import numpy as np
PH = {
 'es': ['¡Hola! ¿Cómo estás?', 'Mucho gusto.', '¡Salud!', '¡Que vivan los novios!', '¿Bailamos?', '¡Está delicioso!', 'Gracias.'],
 'ru': ['Привет! Как дела?', 'Очень приятно.', 'За молодых!', 'Горько!', 'Потанцуем?', 'Очень вкусно!', 'Спасибо.'],
}
VOICES = {'es': ['es-MX-DaliaNeural', 'es-MX-JorgeNeural'], 'ru': ['ru-RU-SvetlanaNeural', 'ru-RU-DmitryNeural']}
os.makedirs('out/audio', exist_ok=True); os.makedirs('w', exist_ok=True)
import edge_tts
from faster_whisper import WhisperModel
import librosa
asr = WhisperModel('medium', device='cpu', compute_type='int8')
def norm(s):
    s = unicodedata.normalize('NFD', s.lower()); s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-zа-яё ]', '', s.replace('ё', 'е')).split()
def pitch(path):
    y, sr = librosa.load(path, sr=16000)
    f0, vf, _ = librosa.pyin(y, fmin=70, fmax=450, sr=sr, frame_length=1024)
    f = f0[~np.isnan(f0)]
    if len(f) < 6: return None
    st = 12 * np.log2(f / np.median(f))
    n = len(st); tail = st[int(n * 0.7):]; mid = st[int(n * 0.35):int(n * 0.7)]
    return {'end_vs_mid_st': round(float(np.mean(tail[-max(2, len(tail)//2):]) - np.mean(mid)), 1), 'last_st': round(float(np.mean(st[-3:])), 1), 'range_st': round(float(st.max() - st.min()), 1)}
async def synth(text, voice, path):
    await edge_tts.Communicate(text, voice, rate='-12%').save(path)
report = {}
for lang, voices in VOICES.items():
    for voice in voices:
        res = []
        for i, t in enumerate(PH[lang]):
            raw = 'w/%s-%d.mp3' % (voice, i)
            asyncio.run(synth(t, voice, raw))
            w16 = raw.replace('.mp3', '.wav')
            subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', raw, '-ac', '1', '-ar', '16000', '-acodec', 'pcm_s16le', w16], check=True)
            mp3 = 'out/audio/%s-%02d.mp3' % (voice, i)
            # trim silence at both ends, keep a short pad, normalize loudness
            subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', raw, '-af', 'silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.05,areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.12,areverse,loudnorm=I=-16:TP=-1.5', '-ac', '1', '-ar', '24000', '-b:a', '48k', mp3], check=True)
            with wave.open(w16) as w: pcm = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
            segs, _ = asr.transcribe(pcm, language=lang, beam_size=5)
            heard = ' '.join(s.text for s in segs).strip()
            res.append({'i': i, 'text': t, 'heard': heard, 'ok': norm(heard) == norm(t), 'pitch': pitch(w16), 'kb': round(os.path.getsize(mp3) / 1024, 1)})
            print(voice, i, 'OK ' if res[-1]['ok'] else 'BAD', t, '->', heard, res[-1]['pitch'])
        report[voice] = res
json.dump(report, open('out/report.json', 'w'), ensure_ascii=False, indent=1)
