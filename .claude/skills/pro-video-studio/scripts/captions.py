"""Animated word-level captions (ASS) from words.json. Usage:
  captions.py words.json out.ass --style reel|luxury|karaoke|minimal [--w 1080 --h 1920] [--per 3] [--y 0.72]
Burn: ffmpeg -i in.mp4 -vf "ass=out.ass" ...  (fonts: Montserrat, Poppins, Bebas Neue, Playfair Display, Cormorant Garamond, Cinzel)"""
import argparse, json
p = argparse.ArgumentParser(); p.add_argument("words"); p.add_argument("out")
p.add_argument("--style", default="reel"); p.add_argument("--w", type=int, default=1080); p.add_argument("--h", type=int, default=1920)
p.add_argument("--per", type=int, default=3); p.add_argument("--y", type=float, default=0.72); p.add_argument("--accent", default="00D7FF")  # BGR hex
a = p.parse_args(); W, H = a.w, a.h; S = min(W, H)
ST = {  # font, size, primary, outline, outline_w, shadow, upper, spacing
 "reel":    ("Montserrat ExtraBold", .085, "FFFFFF", "000000", 6, 2, True, 0),
 "karaoke": ("Poppins Bold",         .075, "FFFFFF", "000000", 5, 0, True, 0),
 "luxury":  ("Playfair Display",     .070, "F2ECE4", "000000", 0, 1, False, 4),
 "minimal": ("Inter SemiBold",       .050, "FFFFFF", "000000", 3, 0, False, 0)}[a.style]
font, sz, prim, outl, ow, sh, up, sp = ST; fs = int(S * sz)
def t(x): h, r = divmod(x, 3600); m, s = divmod(r, 60); return f"{int(h)}:{int(m):02}:{s:05.2f}"
hdr = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: C,{font},{fs},&H00{prim},&H00{a.accent},&H00{outl},&H64000000,0,0,0,0,100,100,{sp},0,1,{ow},{sh},5,60,60,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
ws = json.load(open(a.words))["words"]; ev = []; pos = f"\\pos({W//2},{int(H*a.y)})"
groups = [ws[i:i + a.per] for i in range(0, len(ws), a.per)]
for g in groups:
    txt = [ (w["word"].upper() if up else w["word"]) for w in g ]; g0, g1 = g[0]["start"], g[-1]["end"]
    if a.style == "luxury":  # whole phrase, slow fade + gentle rise + tracking-in
        ev.append(f"Dialogue: 0,{t(g0)},{t(g1+.25)},C,,0,0,0,,{{\\move({W//2},{int(H*a.y)+12},{W//2},{int(H*a.y)},0,400)\\fad(350,250)\\fsp{sp+6}\\t(0,600,\\fsp{sp})}}{' '.join(txt)}")
    elif a.style == "karaoke":
        k = "".join(f"{{\\kf{max(1,int((w['end']-w['start'])*100))}}}{x} " for w, x in zip(g, txt))
        ev.append(f"Dialogue: 0,{t(g0)},{t(g1)},C,,0,0,0,,{{{pos}\\fad(80,80)}}{k.strip()}")
    else:  # reel / minimal: active word highlighted + pop
        for j, w in enumerate(g):
            end = g[j+1]["start"] if j+1 < len(g) else g1
            parts = [(f"{{\\c&H00{a.accent}&\\fscx112\\fscy112}}{x}{{\\r}}" if k == j else x) for k, x in enumerate(txt)]
            pop = "\\fscx92\\fscy92\\t(0,90,\\fscx100\\fscy100)" if j == 0 and a.style == "reel" else ""
            ev.append(f"Dialogue: 0,{t(w['start'])},{t(end)},C,,0,0,0,,{{{pos}{pop}}}{' '.join(parts)}")
open(a.out, "w").write(hdr + "\n".join(ev) + "\n"); print(f"{len(ev)} caption events -> {a.out}")
