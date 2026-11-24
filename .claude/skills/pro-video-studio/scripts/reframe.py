"""Face-tracked smart reframe. Usage: reframe.py IN OUT [--aspect 9:16|1:1|4:5|16:9] [--height 1920]
Detects faces (OpenCV), smooths the camera path, renders with ffmpeg (high quality, audio copied)."""
import argparse, subprocess, json, cv2, numpy as np, os, tempfile
p = argparse.ArgumentParser(); p.add_argument("inp"); p.add_argument("out"); p.add_argument("--aspect", default="9:16")
p.add_argument("--height", type=int, default=1920); p.add_argument("--smooth", type=float, default=1.2); a = p.parse_args()
aw, ah = map(int, a.aspect.split(":")); cap = cv2.VideoCapture(a.inp)
W, H, fps = int(cap.get(3)), int(cap.get(4)), cap.get(5) or 30
if W / H > aw / ah: cw, ch = int(H * aw / ah) // 2 * 2, H
else: cw, ch = W, int(W * ah / aw) // 2 * 2
det = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
step = max(1, int(fps / 5)); xs, ts = [], []; i = 0
while True:
    ok = cap.grab()
    if not ok: break
    if i % step == 0:
        _, f = cap.retrieve(); g = cv2.cvtColor(cv2.resize(f, (W // 2, H // 2)), cv2.COLOR_BGR2GRAY)
        fc = det.detectMultiScale(g, 1.1, 6, minSize=(40, 40))
        if len(fc): x, y, w, h = max(fc, key=lambda r: r[2] * r[3]); xs.append((x + w / 2) * 2); ts.append(i / fps)
    i += 1
dur = i / fps
if not xs: xs, ts = [W / 2], [0]
grid = np.arange(0, dur + .2, .2); cx = np.interp(grid, ts, xs)
k = max(1, int(a.smooth / .2)); cx = np.convolve(np.pad(cx, k, mode="edge"), np.ones(2 * k + 1) / (2 * k + 1), "valid")
cx = np.clip(cx - cw / 2, 0, W - cw)
cmd = tempfile.NamedTemporaryFile("w", suffix=".cmd", delete=False)
for tt, x in zip(grid, cx): cmd.write(f"{tt:.2f} crop x {int(x)};\n")
cmd.close(); oh = a.height; ow = int(oh * aw / ah) // 2 * 2
vf = f"sendcmd=f={cmd.name},crop={cw}:{ch}:{int(cx[0])}:{(H-ch)//2},scale={ow}:{oh}:flags=lanczos,setsar=1"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a.inp, "-vf", vf, "-c:v", "libx264", "-crf", "16", "-preset", "slow",
                "-pix_fmt", "yuv420p", "-c:a", "copy", a.out], check=True)
os.unlink(cmd.name); print(f"faces found in {len(ts)} samples -> {a.out} ({ow}x{oh})")
