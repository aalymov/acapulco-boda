# «Горько» candidates: the word cut out of phrases where context gives the stress (ГО-рько), plus whole-word takes
import os, json, subprocess, asyncio, wave, time
import numpy as np, edge_tts
from faster_whisper import WhisperModel
os.makedirs('out/audio', exist_ok=True); os.makedirs('w', exist_ok=True)
asr = WhisperModel('medium', device='cpu', compute_type='int8')
C = [
 ('cut', 'ru-RU-DmitryNeural', 'Гости кричат: «Горько!»'),
 ('cut', 'ru-RU-DmitryNeural', 'Горько! Горько! Горько!'),
 ('cut', 'ru-RU-DmitryNeural', 'И все закричали: горько!'),
 ('cut', 'ru-RU-DmitryNeural', 'На свадьбе кричат «горько», и молодые целуются.'),
 ('cut', 'ru-RU-DmitryNeural', 'Мне очень горько.'),
 ('whole', 'ru-RU-SvetlanaNeural', 'Горько!'),
]
async def synth(text, voice, path): await edge_tts.Communicate(text, voice, rate='-12%').save(path)
def say(text, voice, path):
    for a in range(5):
        try: asyncio.run(synth(text, voice, path)); return True
        except Exception as e: print('retry', a, type(e).__name__); time.sleep(4 + 3 * a)
    return False
rep = []
for k, (how, voice, text) in enumerate(C):
    p = 'w/%d.mp3' % k
    if not say(text, voice, p): print(k, 'FAILED', text); continue
    time.sleep(2)
    wv = p + '.wav'; subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', p, '-ac', '1', '-ar', '24000', '-acodec', 'pcm_s16le', wv], check=True)
    out = 'out/audio/c%d.mp3' % k
    if how == 'cut':
        with wave.open(wv) as w: sr = w.getframerate(); pcm = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
        y16 = pcm[::3] if sr == 48000 else None
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', p, '-ac', '1', '-ar', '16000', '-acodec', 'pcm_s16le', wv + '16.wav'], check=True)
        with wave.open(wv + '16.wav') as w: a16 = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
        segs, _ = asr.transcribe(a16, language='ru', beam_size=5, word_timestamps=True)
        words = [wd for s in segs for wd in s.words]
        hit = [wd for wd in words if 'горьк' in wd.word.lower()]
        print(k, text, '| words:', [(wd.word, round(wd.start, 2), round(wd.end, 2)) for wd in words])
        if not hit: continue
        wd = hit[0]; a = max(0, wd.start - 0.04); b = wd.end + 0.08
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', p, '-ss', '%.3f' % a, '-to', '%.3f' % b, '-af', 'afade=t=in:d=0.015,areverse,afade=t=in:d=0.04,areverse,loudnorm=I=-16:TP=-1.5', '-ac', '1', '-ar', '24000', '-b:a', '48k', out], check=True)
    else:
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', p, '-af', 'silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.08,areverse,silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.15,areverse,loudnorm=I=-16:TP=-1.5', '-ac', '1', '-ar', '24000', '-b:a', '48k', out], check=True)
    # what does the recognizer hear in the final clip
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', out, '-ac', '1', '-ar', '16000', '-acodec', 'pcm_s16le', out + '.wav'], check=True)
    with wave.open(out + '.wav') as w: c16 = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    heard = ' '.join(s.text for s in asr.transcribe(c16, language='ru', beam_size=5)[0]).strip()
    os.remove(out + '.wav')
    row = {'k': k, 'how': how, 'voice': voice, 'from': text, 'heard': heard, 'sec': round(len(c16) / 16000, 2)}
    print(json.dumps(row, ensure_ascii=False)); rep.append(row)
json.dump(rep, open('out/report.json', 'w'), ensure_ascii=False, indent=1)
