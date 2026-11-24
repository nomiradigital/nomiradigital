---
name: pro-video-studio
description: Professional video finishing toolkit — free local transcription (Whisper), silence removal (auto-editor), face-tracked 9:16/1:1/4:5 reframe, cinematic LUT grading (luxury/golden/noir/clean), animated word-level captions (reel/luxury/karaoke/minimal), audio cleanup and -14 LUFS mastering, platform export presets (IG Reels, TikTok, YouTube, ProRes master). Use for Instagram Reels, TikTok, luxury fashion ads, captions/subtitles, colour and audio fixes, aspect conversion and final MP4 export. Combine with Herk skills (short-form-edit, edit-video, hyperframes) for motion graphics and with video-use for conversational cutting.
---

# Pro Video Studio

Always start with: `source .claude/skills/pro-video-studio/scripts/env.sh` (sets `$PVS_PY`, `$PVS`, model paths).
Write all outputs to `<footage_dir>/edit/`. Never overwrite source footage. Show the user a plan before a full render; render a 5-second draft first for look approval.

## Tool map
| Job | Tool |
|---|---|
| Transcribe (free, local, Hindi/English/auto) | `$PVS_PY $PVS/transcribe.py IN --model small|medium --lang auto` → `words.json`, `captions.srt` |
| Remove silence / dead air | `auto-editor IN --edit audio:threshold=0.04 --margin 0.2s -o OUT --no-open` (export to Premiere/Resolve: `--export premiere` / `resolve`) |
| Remove mistakes, retakes | Herk `/cut-mistakes` (review-gated) or `video-use` |
| Scene detection (B-roll, montage) | `scenedetect -i IN detect-adaptive list-scenes split-video` |
| Smart reframe | `$PVS_PY $PVS/reframe.py IN OUT --aspect 9:16|1:1|4:5|16:9` (face tracking, smoothed) |
| Animated captions | `$PVS_PY $PVS/captions.py words.json OUT.ass --style reel|luxury|karaoke|minimal [--per 3 --y 0.72 --accent 00D7FF]` then `ass=OUT.ass` filter |
| Colour grade | `lut3d=/opt/video-tools/luts/{luxury,golden,noir,clean}.cube` |
| Export | `$PVS/export.sh reel|square|feed|yt|4k|master IN OUT "extra,filters"` (-14 LUFS, -1 dBTP) |
| Motion graphics, titles, transitions | Herk `/hyperframes`, `/short-form-edit`, `/motion-showreel`; Remotion via `npx create-video@latest` |
| Timeline editor / human review | OpenChatCut MCP (start server: see below) |
| Voiceover (free) | Kokoro: models in `$PVS_MODELS/kokoro-v1.0.onnx`, `voices-v1.0.bin` |
| Background removal (stills/product) | `rembg i in.png out.png` |
| Download reference/online sources | `yt-dlp URL` (only content the user owns or has rights to) |

## Kinetic captions + motion graphics (reference-matched reels)
`kinetic.py` builds a HyperFrames composition over the footage. Two looks:
- `neon`: Montserrat ExtraBold, words pop in as spoken, lime `#D7FF3C` glowing keyword (~150px), white small lines (~60px), red strike-through, face ring + coral pill, REC camera frame, red glass alert pills, glowing line icons, punch-in zoom.
- `cine`: Poppins lead-in (~62px), huge Barlow Condensed ExtraBold Italic uppercase keyword (~230px, auto-fit) with white→cyan gradient and blue glow, light sweep, glowing filled icons, punch-in zoom.
Flow (9:16 source, after cutting):
1. `$PVS_PY $PVS/transcribe.py cut.mp4 --out edit` → `$PVS_PY $PVS/kinetic.py plan edit/words.json edit/plan.json`
2. Edit `plan.json` like an editor: one idea per group, keyword = the emotional/meaning word, `fx` (`strike` on negatives, `ring`+`pill` on reactions, `rec` for recording talk, `alert` list for pain points, `zoom` every 2–3 groups), `icon` (send/alert/x/chat/question/star), `pos` top when ring is used.
3. `$PVS_PY $PVS/kinetic.py build cut.mp4 edit/plan.json edit/kin --look neon|cine --sfx`
4. `cd edit/kin && npx --yes hyperframes lint && npx --yes hyperframes snapshot --at T1,T2 --no-end --output snaps` (check frames), then `npx --yes hyperframes render --quality high --output renders/overlay.mp4 && ./finish.sh` → `final.mp4` (audio + whoosh/pop SFX, -14 LUFS).
Hindi/Hinglish: transcribe with `--lang hi` (Devanagari) or `--lang en` for Roman Hinglish captions; check spelling in plan before build.

## Look recipes (append to export extra filters)
- **Luxury fashion**: `lut3d=/opt/video-tools/luts/luxury.cube,unsharp=5:5:0.4,noise=alls=5:allf=t,vignette=PI/5` + captions `--style luxury`. Slow pacing (1.5–3 s shots), 24/25 fps feel, slow push-ins (`zoompan=z='min(zoom+0.0008,1.08)':d=1:s=1080x1920`), letterbox optional `pad`/`drawbox`. Music low, ambient SFX (fabric, heels), no busy emojis.
- **Golden editorial**: `lut3d=.../golden.cube,colortemperature=temperature=5200`.
- **Noir / B&W campaign**: `lut3d=.../noir.cube,noise=alls=8:allf=t`.
- **Clean commercial / UGC reel**: `lut3d=.../clean.cube` + captions `--style reel`; cuts every 0.8–2 s, punch-in zooms on emphasis (`crop` 1.1×), hook in first 1.5 s.
- **Fix lighting**: `eq=brightness=0.04:contrast=1.08:gamma=1.05`, shadows lift `curves=master='0/0.04 0.5/0.52 1/1'`, white balance `colortemperature`, denoise low light `hqdn3d=2:1:3:3` or `nlmeans=s=2`.
- **Stabilise**: pass 1 `vidstabdetect=result=t.trf`, pass 2 `vidstabtransform=input=t.trf:smoothing=20,unsharp`.
- **Slow motion**: `minterpolate=fps=60:mi_mode=mci` then `setpts=2*PTS`.

## Audio recipes
- Voice cleanup: `highpass=f=80,arnndn=m=$PVS_RNNOISE/somnolent-hogwash-2018-09-01/sh.rnnn,afftdn=nf=-25,acompressor=threshold=-18dB:ratio=3:attack=5:release=80,equalizer=f=3000:t=q:w=1:g=2`.
- Music ducking under voice: `[music][voice]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=300[ducked]` then `amix`.
- Mastering is in `export.sh` (`loudnorm` -14 LUFS). For exact target, run two-pass loudnorm.
- SFX: whooshes on transitions, risers before reveals; keep SFX ~ -18 dB under voice.

## Transitions
`xfade=transition=fade|fadeblack|smoothleft|circleopen|dissolve|zoomin|slideup:duration=0.4:offset=T` (+ `acrossfade=d=0.4` for audio). Luxury: `fade`/`fadeblack`/`dissolve` 0.5–0.8 s. Reels: hard cuts + occasional `zoomin`/`slideup` 0.2–0.3 s.

## Workflow for a client edit
1. `ffprobe` every source; note fps, resolution, colour space (HDR/log → `zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=hable,zscale=t=bt709:m=bt709:r=tv,format=yuv420p`).
2. Transcribe → propose structure (hook, story, CTA) → user approves.
3. Cut (auto-editor / Herk cut-mistakes / video-use) → reframe per platform → grade → captions → music/SFX → export.
4. Verify: watch frames (`ffmpeg -ss T -frames:v 1`), check caption timing, `ebur128` loudness, file plays, correct size.
5. Deliver `edit/final_<platform>.mp4`; offer variants (9:16, 1:1, 16:9) from the same master.

## Paid services
ElevenLabs (Scribe, voice), Kie.ai, OpenChatCut built-in agent model keys, Fal.ai are optional and paid. Never use them without the user's explicit OK; the free local path above covers everything.

## OpenChatCut server
`PATH=/opt/node24/node_modules/node/bin:$PATH npm --prefix /opt/video-tools/OpenChatCut run dev` (background). MCP `openchatcut` connects at `http://localhost:5199/api/external-mcp/mcp`.
