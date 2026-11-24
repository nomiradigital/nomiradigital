"""Generate 33^3 .cube LUTs: luxury (warm highlights, deep teal shadows, soft contrast),
golden (warm editorial), noir (rich B&W), clean (bright commercial). Usage: luts.py OUTDIR"""
import sys, os, numpy as np
out = sys.argv[1]; os.makedirs(out, exist_ok=True); N = 33
r, g, b = np.meshgrid(*(np.linspace(0, 1, N),) * 3, indexing="ij"); rgb = np.stack([r, g, b], -1)
def s(x, k): return 0.5 + (x - .5) * (1 + k) - k * 4 * (x - .5) ** 3          # soft S-curve
def lum(x): return (x * [.2126, .7152, .0722]).sum(-1, keepdims=True)
def sat(x, k): L = lum(x); return L + (x - L) * k
def split(x, sh, hi): L = lum(x); return x + (1 - L) ** 2 * np.array(sh) + L ** 2 * np.array(hi)
LUT = {
 "luxury": lambda x: sat(split(s(x * .97 + .02, .35), [-.03, .01, .04], [.05, .02, -.03]), .9),
 "golden": lambda x: sat(split(s(x, .25), [.0, -.01, -.02], [.07, .035, -.04]), 1.08),
 "noir":   lambda x: np.repeat(s(lum(x) * 1.02, .6), 3, -1),
 "clean":  lambda x: sat(s(x * .95 + .05, .15), 1.12)}
for n, f in LUT.items():
    v = np.clip(f(rgb), 0, 1).transpose(2, 1, 0, 3).reshape(-1, 3)  # cube order: R fastest
    with open(f"{out}/{n}.cube", "w") as fh:
        fh.write(f'TITLE "{n}"\nLUT_3D_SIZE {N}\n'); fh.writelines(f"{a:.6f} {b:.6f} {c:.6f}\n" for a, b, c in v)
print("LUTs:", ", ".join(f"{out}/{n}.cube" for n in LUT))
