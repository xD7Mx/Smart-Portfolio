#!/usr/bin/env python3
"""السلامةُ الماليةُ بخمسة محاور (D469) — أحكامُها على جدولٍ معلوم.

    python3 scripts/audit/health_logic.py

القاعدةُ مستخرجةٌ من صور «InvestingPro» وموافَقٌ عليها: درجةُ المقياس = 5 × نقطتِه
المئوية (أو 5 × (1 − النقطة) لما الأقلُّ فيه أفضل)، والمحورُ متوسّطُ مقاييسه،
والكلُّ متوسّطُ المحاور. ونزيد: كلُّ محورٍ يُشرح بأقوى مقياسٍ وأضعفه.
"""
import os as _os, tempfile as _tf
_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX
_os.environ["SP_STATUS_LOG"] = _os.path.join(_SANDBOX, "status_codes.jsonl")
import pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend")); sys.path.insert(0, "/app")
try:
    import app  # noqa: F401
except ModuleNotFoundError as e:
    print(f"⚠ بيئةٌ ناقصة ({e.name}) — لم يُقَس"); sys.exit(0)
try:
    from app.services import financial_health as H
except ImportError:
    print("FAIL D469 — لا محرّكَ للسلامة المالية"); sys.exit(1)

fail = 0
def check(ok, label, det=""):
    global fail
    if not ok: fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))

T = {s: {"pe": pe, "roe": roe, "rev_growth": g, "fcf_margin": f, "pos_52w": p}
     for s, pe, roe, g, f, p in (("A", 10, .30, .10, .08, .9), ("B", 20, .20, .05, .05, .5),
                                 ("C", 30, .10, .00, .02, .2), ("D", 40, .05, -.05, -.01, .1),
                                 ("E", 50, .15, .02, .03, .4))}
r = H.score("A", T)
pe = next(m for p in r["pillars"] for m in p["metrics"] if m["key"] == "pe")
check(abs(pe["score"] - 5 * (1 - 0.1)) < 1e-6, "١ المقياسُ الذي الأقلُّ فيه أفضل: 5 × (1 − النقطة المئوية)", str(pe["score"]))
roe = next(m for p in r["pillars"] for m in p["metrics"] if m["key"] == "roe")
check(abs(roe["score"] - 5 * 0.9) < 1e-6, "٢ والأعلى أفضل: 5 × النقطة المئوية", str(roe["score"]))
check(abs(r["score"] - sum(p["score"] for p in r["pillars"]) / len(r["pillars"])) < 0.01,
      "٣ الدرجةُ الكلّية متوسّطُ المحاور (كما في «InvestingPro»: 1.86)")
check(all(p["why"] and "أقوى" in p["why"] and "أضعف" in p["why"] for p in r["pillars"]),
      "٤ وكلُّ محورٍ يُشرح بأقوى مقياسٍ وأضعفه")
check(H.label(0.56) == "ضعيف" and H.label(1.86) == "عادل" and H.label(4.2) == "ممتاز", "٥ الوصفُ من الدرجة")
check(H.score("A", {"A": T["A"], "B": T["B"]}) is None, "٦ ولا ترتيبَ بأقلّ من أربعة أقران")
TB = {s: {"pe": pe, "roe": roe, "ebit_margin": em, "ocf_to_ni": oq, "fcf_margin": fm}
      for s, pe, roe, em, oq, fm in (("1120", 16, .16, .96, -.9, -.46), ("1180", 12, .14, .80, 1.2, .3),
                                     ("1010", 9, .12, .7, .5, .1), ("1060", 10, .11, .6, -.2, -.1), ("1080", 8, .10, .5, .8, .2))}
rb = H.score("1120", TB, "bank")
keys = {m["key"] for p in rb["pillars"] for m in p["metrics"]}
check(not keys & H.FIN_SKIP and "cash" not in {p["pillar"] for p in rb["pillars"]},
      "٧ المصرفُ لا يُقاس بهامشٍ تشغيليٍّ ولا تدفّقٍ حرّ (الراجحي: هامشٌ 96٪ وجودةُ أرباحٍ سالبة)", str(sorted(keys)))
print(f"{'FAIL' if fail else 'PASS'} D469 — السلامةُ الماليةُ بخمسة محاور")
sys.exit(fail)
