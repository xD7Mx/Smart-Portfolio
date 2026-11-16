#!/usr/bin/env python3
"""خريطةٌ نصّيةٌ لرسم الجزيرة كابيتال (‏D755) — قارئٌ فقط: كلُّ خليّةٍ (5 بكسل عرضاً = شمعة) رمزُ أبرز ما فيها:
G أخضرُ الرسم · R أحمرُ الرسم · B أزرق · L أخضرُ فاتح (متوسّط) · P أحمرُ فاتح (متوسّط) · u شمعةٌ صاعدة · d هابطة · K داكن (خطوطٌ سوداء) · . فارغ.
فتُرى الأسهمُ وخطوطُ التباعد والقنوات بمواضعها بلا قارئٍ بصريّ."""
import glob, os, sys   # noqa: E401
import numpy as np
from PIL import Image
D = os.path.join(os.environ.get("SP_STATE_DIR", "/app/storage"), "ajc_charts")
fs = sorted(glob.glob(os.path.join(D, "20*.png")))
for f in [fs[-1], [x for x in fs if "2026-10-1" in x][0]]:
    im = Image.open(f).convert("RGB")
    A = np.asarray(im, dtype=np.int16)
    H, W, _ = A.shape
    d = lambda c: np.abs(A - np.array(c, dtype=np.int16)).sum(axis=2)   # noqa: E731
    masks = [("G", d((74, 175, 79)) <= 30), ("R", d((239, 56, 70)) <= 30), ("K", A.sum(axis=2) <= 200),
             ("B", d((70, 102, 176)) <= 40), ("u", d((33, 171, 148)) <= 30), ("d", d((239, 84, 81)) <= 30),
             ("L", d((165, 214, 167)) <= 45), ("P", d((245, 148, 146)) <= 40)]
    print("\n══", os.path.basename(f), W, H, "══")
    x0, cw = 440, 5
    for y0, y1, rh in ((0, 415, 7), (512, 605, 6)):
        for yy in range(y0, y1, rh):
            row = []
            for xx in range(x0, min(W, 1240), cw):
                ch = "."
                for s, m in masks:
                    if m[yy:yy + rh, xx:xx + cw].any():
                        ch = s
                        break
                row.append(ch)
            print(f"{yy:3d} " + "".join(row))
        print("----")
