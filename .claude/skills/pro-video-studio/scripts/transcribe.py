"""Local, free word-level transcription (faster-whisper). Usage:
  transcribe.py INPUT [--model small|medium] [--lang hi|en|auto] [--out DIR]
Writes words.json (word, start, end, prob) and captions.srt."""
import argparse, json, os
from faster_whisper import WhisperModel
p = argparse.ArgumentParser(); p.add_argument("input"); p.add_argument("--model", default="small")
p.add_argument("--lang", default="auto"); p.add_argument("--out", default=None); a = p.parse_args()
out = a.out or os.path.join(os.path.dirname(os.path.abspath(a.input)), "edit"); os.makedirs(out, exist_ok=True)
m = WhisperModel(a.model, device="cpu", compute_type="int8")
segs, info = m.transcribe(a.input, language=None if a.lang == "auto" else a.lang, word_timestamps=True, vad_filter=True)
words, srt = [], []
def ts(t): h, r = divmod(t, 3600); mi, s = divmod(r, 60); return f"{int(h):02}:{int(mi):02}:{s:06.3f}".replace(".", ",")
for i, s in enumerate(segs, 1):
    srt.append(f"{i}\n{ts(s.start)} --> {ts(s.end)}\n{s.text.strip()}\n")
    words += [{"word": w.word.strip(), "start": round(w.start, 3), "end": round(w.end, 3), "prob": round(w.probability, 3)} for w in s.words]
json.dump({"language": info.language, "duration": info.duration, "words": words}, open(f"{out}/words.json", "w"), ensure_ascii=False, indent=1)
open(f"{out}/captions.srt", "w").write("\n".join(srt))
print(f"lang={info.language} words={len(words)} -> {out}/words.json, captions.srt")
