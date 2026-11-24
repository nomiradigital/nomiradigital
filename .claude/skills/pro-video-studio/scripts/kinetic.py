"""Kinetic caption + motion-graphics builder (HyperFrames) for talking-head reels.

Two looks, matched to the reference reels:
  neon  - mixed-size words popping in as spoken, lime glowing keyword, red strike-through,
          face ring + pill, glass alert pills, REC camera frame, punch-in zooms.
  cine  - small white lead-in line, huge condensed italic keyword with cyan glow,
          glowing icons, soft light sweep, punch-in zooms.

Steps:
  1) plan:   kinetic.py plan  words.json plan.json [--max 5]          (auto-groups words, picks keywords)
     -> edit plan.json by hand: key word index, fx list, pos, pill text, icon
  2) build:  kinetic.py build VIDEO plan.json OUTDIR --look neon|cine [--sfx]
  3) render: cd OUTDIR && npx --yes hyperframes render --quality high --output renders/overlay.mp4
             then OUTDIR/finish.sh  (muxes original audio + optional SFX, -14 LUFS, final.mp4)

plan.json group fields: words [i,j] (inclusive indices into words.json), key (word index or null),
  pos "mid"|"top"|"low", fx: any of "strike","ring","rec","alert","zoom","icon",
  pill (text for ring pill), alert (list of alert texts), icon ("send","alert","x","chat","question","star").
VIDEO must be 9:16 (use reframe.py first). Footage stays untouched; everything is written to OUTDIR.
"""
import argparse, json, os, shutil, subprocess, html, re

STOP = set("a an the to of in on at for and or but is are was were be been being i you he she it we they me my your our "
           "their this that these those with as by from if so do does did have has had not no yes just very really "
           "can will would should could about into than then there here what when how why who".split())
FONT_DIR = "/opt/video-tools/gfonts/ofl"
FONTS = {"Montserrat": f"{FONT_DIR}/montserrat/Montserrat[wght].ttf",
         "PoppinsSB": f"{FONT_DIR}/poppins/Poppins-SemiBold.ttf",
         "PoppinsM": f"{FONT_DIR}/poppins/Poppins-Medium.ttf",
         "BarlowCXBI": f"{FONT_DIR}/barlowcondensed/BarlowCondensed-ExtraBoldItalic.ttf"}

ICONS = {  # simple stroke SVG paths, 24x24 viewBox
 "send": '<path d="M22 2 11 13M22 2l-7 20-4-9-9-4 20-7z"/>',
 "alert": '<path d="M12 3 2 21h20L12 3z"/><path d="M12 10v5M12 18h.01"/>',
 "x": '<path d="M6 6l12 12M18 6 6 18"/>',
 "chat": '<path d="M21 12a8 8 0 0 1-11.6 7.1L4 21l1.9-5.4A8 8 0 1 1 21 12z"/><path d="M8 12h.01M12 12h.01M16 12h.01"/>',
 "question": '<path d="M9 9a3 3 0 1 1 4.5 2.6c-.9.5-1.5 1.2-1.5 2.4"/><path d="M12 18h.01"/>',
 "star": '<path d="m12 2 3 7 7 .6-5.3 4.6 1.6 7.1L12 17.6 5.7 21.3l1.6-7.1L2 9.6 9 9z"/>'}


def plan(words_path, out, maxw):
    ws = json.load(open(words_path))["words"]
    groups, cur = [], []
    for i, w in enumerate(ws):
        cur.append(i)
        gap = ws[i + 1]["start"] - w["end"] if i + 1 < len(ws) else 9
        if len(cur) >= maxw or re.search(r"[.,!?;:]$", w["word"]) or gap > 0.35:
            groups.append(cur); cur = []
    if cur: groups.append(cur)
    out_g = []
    for n, g in enumerate(groups):
        cands = [i for i in g if re.sub(r"\W", "", ws[i]["word"]).lower() not in STOP]
        key = max(cands, key=lambda i: len(ws[i]["word"])) if cands else None
        out_g.append({"words": [g[0], g[-1]], "text": " ".join(ws[i]["word"] for i in g), "key": key,
                      "pos": "mid", "fx": ["zoom"] if n % 3 == 1 else []})
    json.dump({"groups": out_g}, open(out, "w"), indent=1, ensure_ascii=False)
    print(f"{len(out_g)} groups -> {out} (edit keys/fx, then build)")


def face_center(video, t):
    try:
        import cv2
        c = cv2.VideoCapture(video); c.set(cv2.CAP_PROP_POS_MSEC, t * 1000); ok, f = c.read()
        if not ok: return None
        det = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        fc = det.detectMultiScale(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY), 1.1, 6, minSize=(60, 60))
        if not len(fc): return None
        x, y, w, h = max(fc, key=lambda r: r[2] * r[3]); s = 1080 / f.shape[1]
        return (x + w / 2) * s, (y + h / 2) * s, max(w, h) * s
    except Exception:
        return None


def esc(s): return html.escape(s, quote=True)


def build(video, plan_path, outdir, look, sfx):
    P = json.load(open(plan_path)); words_path = P.get("words_json") or os.path.join(os.path.dirname(os.path.abspath(plan_path)), "words.json")
    ws = json.load(open(words_path))["words"]
    dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video]))
    os.makedirs(f"{outdir}/assets", exist_ok=True)
    # dense keyframes = fast, reliable frame extraction in the renderer
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-c:v", "libx264", "-crf", "14", "-preset", "fast", "-r", "30",
                    "-g", "30", "-keyint_min", "30", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "320k", "-movflags", "+faststart",
                    f"{outdir}/assets/src.mp4"], check=True)
    gsap = "/opt/video-tools/herk-edit-kit/video-projects/demo/assets/gsap.min.js"
    shutil.copy(gsap, f"{outdir}/assets/gsap.min.js")
    ff = ""
    for name, path in FONTS.items():
        dst = os.path.basename(path).replace("[", "").replace("]", ""); shutil.copy(path, f"{outdir}/assets/{dst}")
        ff += f"@font-face{{font-family:'{name}';src:url('assets/{dst}');font-weight:100 900}}\n"

    neon = look == "neon"
    css = ff + f"""
*{{box-sizing:border-box;margin:0}}html,body{{width:1080px;height:1920px;overflow:hidden;background:#000}}
#root{{position:relative;width:1080px;height:1920px;overflow:hidden}}
#vwrap{{position:absolute;inset:0;transform-origin:50% 38%}}#vwrap video{{width:1080px;height:1920px;object-fit:cover}}
.vig{{position:absolute;inset:0;background:radial-gradient(ellipse at 50% 40%,transparent 45%,rgba(0,0,0,.55) 100%),linear-gradient(transparent 55%,rgba(0,0,0,.45))}}
.cap{{position:absolute;left:0;width:1080px;text-align:center;padding:0 70px;opacity:0}}
.line{{display:block;white-space:nowrap;line-height:.98}}
.w{{display:inline-block;margin:0 .12em;transform-origin:50% 80%}}
"""
    if neon:
        css += """
.cap{font-family:Montserrat;font-weight:800;color:#fff;letter-spacing:-1.5px}
.sm{font-size:60px;font-weight:700;text-shadow:0 3px 12px rgba(0,0,0,.6)}
.big{font-size:150px;color:#D7FF3C;letter-spacing:-5px;text-shadow:0 0 22px rgba(215,255,60,.55),0 0 60px rgba(215,255,60,.25),0 4px 14px rgba(0,0,0,.5)}
.acc{color:#D7FF3C;text-shadow:0 0 16px rgba(215,255,60,.5)}
.strike{position:absolute;left:4%;width:92%;height:10px;top:52%;background:linear-gradient(90deg,#ff2d2d,#ff5a3c);border-radius:6px;transform:scaleX(0) rotate(-4deg);transform-origin:0 50%;box-shadow:0 0 14px rgba(255,45,45,.8)}
.ring{position:absolute;border-radius:50%;border:4px solid rgba(255,236,214,.92);box-shadow:0 0 28px rgba(255,220,180,.55),inset 0 0 28px rgba(255,220,180,.35);opacity:0}
.pill{position:absolute;padding:10px 26px;border-radius:40px;background:linear-gradient(180deg,#ff8f7a,#e2564a);color:#fff;font:600 30px PoppinsSB;opacity:0;box-shadow:0 6px 20px rgba(0,0,0,.35)}
.rec{position:absolute;inset:70px 60px 120px;opacity:0}
.rec i{position:absolute;width:90px;height:90px;border-color:#fff;border-style:solid;opacity:.9}
.rec .a{left:0;top:0;border-width:5px 0 0 5px}.rec .b{right:0;top:0;border-width:5px 5px 0 0}.rec .c{left:0;bottom:0;border-width:0 0 5px 5px}.rec .d{right:0;bottom:0;border-width:0 5px 5px 0}
.rec b{position:absolute;left:40px;top:34px;font:700 40px Montserrat;color:#fff;text-shadow:0 2px 8px rgba(0,0,0,.6);letter-spacing:1px}
.rec b:before{content:'';display:inline-block;width:18px;height:18px;border-radius:50%;background:#ff2d2d;margin-right:12px;box-shadow:0 0 12px #ff2d2d}
.alert{position:absolute;left:170px;width:740px;height:96px;border-radius:24px;opacity:0;display:flex;align-items:center;gap:26px;padding:0 34px;
 background:linear-gradient(90deg,rgba(40,6,10,.78),rgba(150,14,24,.72));border:1.5px solid rgba(255,90,90,.35);backdrop-filter:blur(10px);box-shadow:0 10px 40px rgba(0,0,0,.45),0 0 30px rgba(255,30,30,.25);
 font:500 40px PoppinsM;color:#fff}
.alert svg{width:44px;height:44px;stroke:#ff3b3b;fill:none;stroke-width:2.4;flex:none;filter:drop-shadow(0 0 8px #ff3b3b)}
.icon{position:absolute;width:110px;height:110px;opacity:0}.icon svg{width:100%;height:100%;stroke:#D7FF3C;fill:none;stroke-width:1.8;filter:drop-shadow(0 0 12px rgba(215,255,60,.8))}
"""
    else:
        css += """
.cap{color:#fff}
.sm{font:500 62px PoppinsM;letter-spacing:.5px;text-shadow:0 3px 14px rgba(0,0,0,.65)}
.big{font:800 italic 230px BarlowCXBI;text-transform:uppercase;letter-spacing:2px;line-height:.92}
.big .w{padding:0 .06em;background:linear-gradient(180deg,#ffffff 30%,#c9f6ff 70%,#7fe3ff);-webkit-background-clip:text;background-clip:text;color:transparent;
 filter:drop-shadow(0 0 18px rgba(80,215,255,.75)) drop-shadow(0 0 46px rgba(40,170,255,.45))}
.acc{color:#bff3ff}
.sweep{position:absolute;inset:0;background:linear-gradient(100deg,transparent 35%,rgba(255,255,255,.22) 50%,transparent 65%);transform:translateX(-120%);mix-blend-mode:screen}
.icon{position:absolute;width:150px;height:150px;opacity:0}.icon svg{width:100%;height:100%;stroke:#e9fbff;fill:rgba(60,190,255,.25);stroke-width:1.6;filter:drop-shadow(0 0 14px #3fc8ff) drop-shadow(0 0 34px rgba(40,140,255,.8))}
.flash{position:absolute;inset:0;background:#fff;opacity:0}
"""
    body, js = [], []
    t = lambda x: f"{x:.3f}"
    sweep_done = False
    for gi, g in enumerate(P["groups"]):
        a, b = g["words"]; idx = list(range(a, b + 1)); key = g.get("key"); fx = set(g.get("fx", []))
        g0 = ws[a]["start"]; nxt = P["groups"][gi + 1]["words"][0] if gi + 1 < len(P["groups"]) else None
        g1 = min(ws[nxt]["start"] if nxt is not None else dur, ws[b]["end"] + 0.6)
        y = {"top": 330, "mid": 1060, "low": 1300}[g.get("pos", "mid")]
        # lines: words before key (small), key (big), words after key (small)
        if key is not None and a <= key <= b:
            pre, post = [i for i in idx if i < key], [i for i in idx if i > key]
            lines = ([("sm", pre)] if pre else []) + [("big", [key])] + ([("sm", post)] if post else [])
        else:
            lines = [("sm", idx)]
        spans = []
        for cls, ids in lines:
            inner = "".join(f'<span class="w" id="w{i}">{esc(ws[i]["word"])}</span>' for i in ids)
            extra = '<i class="strike" id="s%d"></i>' % gi if cls == "big" and "strike" in fx and neon else ""
            fit = ""
            if cls == "big":  # auto-fit long keywords inside 940px safe width
                n = len(ws[ids[0]]["word"]); base, k = (150, .66) if neon else (230, .47)
                fit = f";font-size:{min(base, int(940 / (n * k)))}px"
            spans.append(f'<span class="line {cls}" style="position:relative{fit}">{inner}{extra}</span>')
        body.append(f'<div class="cap" id="g{gi}" style="top:{y}px">{"".join(spans)}</div>')
        js.append(f"tl.set('#g{gi}',{{opacity:1}},{t(g0 - .02)});tl.set('#g{gi}',{{opacity:0}},{t(g1)});")
        for i in idx:
            big = i == key
            if neon:
                js.append(f"tl.from('#w{i}',{{opacity:0,y:{40 if big else 24},scale:{.6 if big else .85},duration:{.22 if big else .14},ease:'back.out(2.2)'}},{t(ws[i]['start'])});")
            else:
                if big:
                    js.append(f"tl.from('#w{i}',{{opacity:0,scale:1.45,y:-10,duration:.32,ease:'expo.out'}},{t(ws[i]['start'])});")
                else:
                    js.append(f"tl.from('#w{i}',{{opacity:0,y:18,duration:.18,ease:'power2.out'}},{t(ws[i]['start'])});")
        kt = ws[key]["start"] if key is not None else g0
        if "zoom" in fx or (key is not None and not neon):
            z = 1.09 if neon else 1.06
            js.append(f"tl.to('#vwrap',{{scale:{z},duration:.25,ease:'power3.out'}},{t(kt)});tl.to('#vwrap',{{scale:1,duration:.35,ease:'power2.inOut'}},{t(max(kt + .3, g1 - .35))});")
        if "strike" in fx and neon:
            js.append(f"tl.to('#s{gi}',{{scaleX:1,duration:.28,ease:'power3.out'}},{t(kt + .45)});")
        if "ring" in fx and neon:
            fc = face_center(video, kt) or (540, 760, 300); cx, cy, fw = fc; r = max(230, fw * 1.15)
            body.append(f'<div class="ring" id="r{gi}" style="left:{cx - r:.0f}px;top:{cy - r:.0f}px;width:{2 * r:.0f}px;height:{2 * r:.0f}px"></div>')
            js.append(f"tl.fromTo('#r{gi}',{{opacity:0,scale:.6,rotation:-20}},{{opacity:1,scale:1,rotation:0,duration:.45,ease:'back.out(1.6)'}},{t(g0)});tl.to('#r{gi}',{{opacity:0,scale:1.08,duration:.25}},{t(g1 - .25)});")
            if g.get("pill"):
                body.append(f'<div class="pill" id="p{gi}" style="left:{cx + r * .45:.0f}px;top:{cy - r * .78:.0f}px">{esc(g["pill"])}</div>')
                js.append(f"tl.fromTo('#p{gi}',{{opacity:0,x:-20,scale:.8}},{{opacity:1,x:0,scale:1,duration:.3,ease:'back.out(2)'}},{t(g0 + .35)});tl.to('#p{gi}',{{opacity:0,duration:.2}},{t(g1 - .2)});")
        if "rec" in fx and neon:
            body.append(f'<div class="rec" id="rec{gi}"><i class="a"></i><i class="b"></i><i class="c"></i><i class="d"></i><b>REC</b></div>')
            js.append(f"tl.to('#rec{gi}',{{opacity:1,duration:.2}},{t(g0)});tl.to('#rec{gi} b',{{opacity:.35,duration:.4,yoyo:true,repeat:{max(1, int((g1 - g0) / .4))}}},{t(g0)});tl.to('#rec{gi}',{{opacity:0,duration:.2}},{t(g1)});")
        for k, txt in enumerate(g.get("alert", []) if neon else []):
            ic = ICONS["alert" if k == 0 else "x"]; at = g0 + .5 + k * .8
            body.append(f'<div class="alert" id="al{gi}_{k}" style="top:{1180 + k * 120}px"><svg viewBox="0 0 24 24">{ic}</svg><span>{esc(txt)}</span></div>')
            js.append(f"tl.fromTo('#al{gi}_{k}',{{opacity:0,y:30,scale:.92}},{{opacity:1,y:0,scale:1,duration:.35,ease:'back.out(1.8)'}},{t(at)});tl.to('#al{gi}_{k}',{{opacity:0,duration:.2}},{t(max(g1, at + .45))});")
        if g.get("icon"):
            ix, iy = (170, y + 230) if neon else (800, y - 190)
            body.append(f'<div class="icon" id="ic{gi}" style="left:{ix}px;top:{iy}px"><svg viewBox="0 0 24 24">{ICONS[g["icon"]]}</svg></div>')
            js.append(f"tl.fromTo('#ic{gi}',{{opacity:0,scale:.3,rotation:-25}},{{opacity:1,scale:1,rotation:0,duration:.4,ease:'back.out(2.4)'}},{t(kt + .05)});tl.to('#ic{gi}',{{y:-14,duration:.6,yoyo:true,repeat:1,ease:'sine.inOut'}},{t(kt + .45)});tl.to('#ic{gi}',{{opacity:0,duration:.2}},{t(g1 - .1)});")
        if not neon and key is not None:
            ir = "" if not sweep_done else ",immediateRender:false"; sweep_done = True
            js.append(f"tl.fromTo('#sweep',{{x:'-120%'}},{{x:'120%',duration:.6,ease:'power2.inOut'{ir}}},{t(kt + .05)});")
    if not neon:
        body.append('<div class="sweep" id="sweep"></div><div class="flash" id="flash"></div>')
        js.insert(0, "tl.fromTo('#flash',{opacity:.9},{opacity:0,duration:.35},0);")
    doc = f"""<!doctype html><html><head><meta charset="utf-8"><title>kinetic</title><script src="assets/gsap.min.js"></script>
<style>{css}</style></head><body>
<div id="root" data-composition-id="main" data-start="0" data-duration="{dur:.3f}" data-width="1080" data-height="1920">
<div id="vwrap"><video id="v" data-start="0" data-duration="{dur:.3f}" data-track-index="0" src="assets/src.mp4" muted playsinline></video></div>
<div class="vig"></div>
{chr(10).join(body)}
</div>
<script>
const tl=gsap.timeline({{paused:true}});
{chr(10).join(js)}
window.__timelines=window.__timelines||{{}};window.__timelines['main']=tl;
</script></body></html>"""
    open(f"{outdir}/index.html", "w").write(doc)
    json.dump({"name": "kinetic"}, open(f"{outdir}/hyperframes.json", "w"))
    # SFX: synthesized whoosh on each keyword, pop on alerts/icons (free, generated locally)
    hits = []
    for g in P["groups"]:
        if g.get("key") is not None: hits.append(("whoosh", ws[g["key"]]["start"] - .12))
        for k, _ in enumerate(g.get("alert", [])): hits.append(("pop", ws[g["words"][0]]["start"] + .5 + k * .8))
        if g.get("icon"): hits.append(("pop", ws[g["key"] if g.get("key") is not None else g["words"][0]]["start"]))
    fin = [
        "#!/bin/bash", "set -e; cd \"$(dirname \"$0\")\"", 'R=renders/overlay.mp4; S=assets/src.mp4',
        "ffmpeg -v error -y -f lavfi -i 'anoisesrc=d=0.45:c=pink:a=0.6' -af 'bandpass=f=1800:w=1600,afade=t=in:d=0.25,afade=t=out:st=0.25:d=0.2,volume=0.35' assets/whoosh.wav",
        "ffmpeg -v error -y -f lavfi -i 'sine=f=900:d=0.09' -af 'afade=t=out:d=0.09,volume=0.4' assets/pop.wav"]
    if sfx and hits:
        ins = " ".join(f"-i assets/{k}.wav" for k, _ in hits)
        fil = ";".join(f"[{n + 1}:a]adelay={max(0, int(s * 1000))}:all=1[s{n}]" for n, (_, s) in enumerate(hits))
        mix = "".join(f"[s{n}]" for n in range(len(hits)))
        fin.append(f"ffmpeg -v error -y -i $S {ins} -filter_complex \"{fil};[0:a]{mix}amix=inputs={len(hits) + 1}:normalize=0,loudnorm=I=-14:TP=-1[a]\" -map '[a]' -ar 48000 assets/mix.wav")
    else:
        fin.append("ffmpeg -v error -y -i $S -af loudnorm=I=-14:TP=-1 -ar 48000 assets/mix.wav")
    fin.append("ffmpeg -v error -y -i $R -i assets/mix.wav -map 0:v -map 1:a -c:v libx264 -crf 17 -preset slow -pix_fmt yuv420p -c:a aac -b:a 320k -shortest -movflags +faststart final.mp4")
    fin.append("ffprobe -v error -show_entries stream=codec_name,width,height:format=duration -of compact final.mp4")
    open(f"{outdir}/finish.sh", "w").write("\n".join(fin) + "\n"); os.chmod(f"{outdir}/finish.sh", 0o755)
    print(f"built {outdir}/index.html ({len(P['groups'])} groups, look={look}); next: render then ./finish.sh")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="cmd", required=True)
    p1 = sp.add_parser("plan"); p1.add_argument("words"); p1.add_argument("out"); p1.add_argument("--max", type=int, default=5)
    p2 = sp.add_parser("build"); p2.add_argument("video"); p2.add_argument("plan"); p2.add_argument("outdir")
    p2.add_argument("--look", default="neon", choices=["neon", "cine"]); p2.add_argument("--sfx", action="store_true")
    a = ap.parse_args()
    plan(a.words, a.out, a.max) if a.cmd == "plan" else build(a.video, a.plan, a.outdir, a.look, a.sfx)
