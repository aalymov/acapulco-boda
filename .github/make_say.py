import os, json, wave, subprocess, urllib.request, re, unicodedata
PH = {
 'es': ['¡Hola! ¿Cómo estás?', 'Mucho gusto', '¡Salud!', '¡Que vivan los novios!', '¿Bailamos?', '¡Está delicioso!', 'Gracias'],
 'ru': ['Привет! Как дела?', 'Очень приятно', 'За молодых!', 'Горько!', 'Потанцуем?', 'Очень вкусно!', 'Спасибо'],
}
VOICES = {
 'es': ['es/es_MX/claude/high/es_MX-claude-high', 'es/es_MX/ald/medium/es_MX-ald-medium'],
 'ru': ['ru/ru_RU/irina/medium/ru_RU-irina-medium', 'ru/ru_RU/ruslan/medium/ru_RU-ruslan-medium', 'ru/ru_RU/dmitri/medium/ru_RU-dmitri-medium', 'ru/ru_RU/denis/medium/ru_RU-denis-medium'],
}
os.makedirs('out/audio', exist_ok=True); os.makedirs('v', exist_ok=True)
from piper import PiperVoice
try:
    from piper import SynthesisConfig
except Exception:
    SynthesisConfig = None
from faster_whisper import WhisperModel
asr = WhisperModel('medium', device='cpu', compute_type='int8')
def norm(s):
    s = unicodedata.normalize('NFD', s.lower()); s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-zа-яё ]', '', s.replace('ё', 'е')).split()
report = {}
for lang, paths in VOICES.items():
    for p in paths:
        name = p.split('/')[-1]
        base = 'https://huggingface.co/rhasspy/piper-voices/resolve/main/' + p
        try:
            urllib.request.urlretrieve(base + '.onnx', 'v/' + name + '.onnx'); urllib.request.urlretrieve(base + '.onnx.json', 'v/' + name + '.onnx.json')
            voice = PiperVoice.load('v/' + name + '.onnx')
        except Exception as e:
            report[name] = {'error': str(e)}; print(name, 'ERR', e); continue
        res = []
        for i, t in enumerate(PH[lang]):
            wav = 'v/%s-%d.wav' % (name, i)
            with wave.open(wav, 'wb') as w:
                if SynthesisConfig is not None and hasattr(voice, 'synthesize_wav'):
                    voice.synthesize_wav(t, w, syn_config=SynthesisConfig(length_scale=1.15))
                else:
                    voice.synthesize(t, w, length_scale=1.15)
            mp3 = 'out/audio/%s-%02d.mp3' % (name, i)
            subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', wav, '-af', 'apad=pad_dur=0.15', '-ac', '1', '-ar', '22050', '-b:a', '48k', mp3], check=True)
            segs, _ = asr.transcribe(wav, language=lang, beam_size=5)
            heard = ' '.join(s.text for s in segs).strip()
            ok = norm(heard) == norm(t)
            with wave.open(wav) as w: dur = w.getnframes() / w.getframerate()
            res.append({'i': i, 'text': t, 'heard': heard, 'ok': ok, 'sec': round(dur, 2), 'kb': round(os.path.getsize(mp3) / 1024, 1)})
            print(name, i, 'OK ' if ok else 'BAD', t, '->', heard)
        report[name] = res
json.dump(report, open('out/report.json', 'w'), ensure_ascii=False, indent=1)
