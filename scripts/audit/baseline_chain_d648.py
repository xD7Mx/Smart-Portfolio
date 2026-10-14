#!/usr/bin/env python3
"""حارسُ D648: سلسلةُ الإصدارات المجمَّدة لا تنكسر — كلُّ أساسٍ جديدٍ يتفوّق على سابقه ولا يتراجع.

حارسُ التجميد (D635) يقارن المرشَّحَ بالأساس، لكنّ الأساسَ نفسَه يُكتب بأمرٍ واحد (`engine_report_save --baseline`):
فلو جُمّد إصدارٌ أضعفُ لصار هو المسطرة وانخفض السقفُ بصمت. فالأساسُ يسمّي سابقَه (`sources.previous`)، وتقريرُ
السابق محفوظٌ ببصمته، ويُقارنان بمقارنة الحارس نفسِها.

‏D707: «مقارنةُ الحارس نفسِها» مرجعُها أيضاً — ‏`reference()`: السابقُ مَقيساً **يومَ تقرير الأساس الجديد نفسَه** إن وُجد شاهدُه
(‏D692)، وموافقةُ المحلّلين ثانويّةٌ حين يحمل الطرفان مقاييسَ النتيجة (‏D700). وكانت السلسلةُ تقارن بأرقام يوم تجميد السابق
(2026-10-10، بلا مقاييس نتيجة)، فأسقطت 2.4 بما أجازه حارسُ التجميد على البيانات نفسِها: الانحرافُ عن أهداف المحلّلين ارتفع
— وهو بالتصميم، فالسعرُ العادلُ حكمُ القوائم لا رأيُ المستقبل — والنتيجةُ بعد سنة ‎+0.03 ← ‎+0.23."""
import json, pathlib, re, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/audit"))
import engine_freeze_d635 as F   # noqa: E402

fail = 0
def check(ok, label, det=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))


def chain(base: dict, reports: pathlib.Path) -> dict:
    """الأساسُ مقابلَ سابقه ← {prev, rep, how, worse, better, info}. المرجعُ مرجعُ حارس التجميد نفسُه (‏D707)."""
    prev = str((base.get("sources") or {}).get("previous") or "")
    m = re.search(r"\b([0-9a-f]{12})\b", prev)
    out = {"prev": prev, "rep": reports / f"{m.group(1)}.json" if m else None}
    if not (out["rep"] and out["rep"].exists()):
        return out
    old = json.loads(out["rep"].read_text(encoding="utf-8"))
    old.setdefault("fingerprint", m.group(1))
    own = reports / f"{base.get('fingerprint')}.json"
    mine = json.loads(own.read_text(encoding="utf-8")) if own.exists() else {"measured_at": base.get("measured_at")}
    saved = F.REPORTS
    F.REPORTS = reports
    del F.INFO[:]
    try:
        ref, out["how"] = F.reference(old, mine)
        # ‏D676: وما قَبِله المالكُ بنصّه في الأساس يُقبل في السلسلة بالشرط نفسِه (أرضيّةٌ ونصّ)
        out["worse"], out["better"] = F.compare(ref, base.get("metrics") or {}, base.get("owner_accepted"))
    finally:
        F.REPORTS = saved
    out["info"] = list(F.INFO)
    return out


base = json.loads(F.BASE.read_text(encoding="utf-8"))
ver = base.get("version")
if ver == "1.0":
    check(True, "١ الإصدارُ الأوّل لا سابقَ له")
else:
    c = chain(base, F.REPORTS)
    check(bool(re.search(r"\b[0-9a-f]{12}\b", c["prev"])), f"١ الأساسُ {ver} يسمّي سابقَه ببصمته", c["prev"] or "لا sources.previous")
    check(bool(c["rep"] and c["rep"].exists()), "٢ وتقريرُ السابق محفوظٌ ببصمته", str(c["rep"]) if c["rep"] else "")
    if "worse" in c:
        print(f"     المرجع: {c['how']}")
        check(not c["worse"], f"٣ الأساسُ {ver} لا يتراجع عن سابقه في شيء", "؛ ".join(c["worse"]))
        check(bool(c["better"]), f"٤ ويتفوّق عليه في مقياسٍ واحدٍ على الأقلّ", {1: "مقياسٌ واحد", 2: "مقياسان"}.get(len(c["better"]), f"{len(c['better'])} مقاييس" if len(c["better"]) <= 10 else f"{len(c['better'])} مقياساً"))
        if c["info"]:
            print("     وللاطّلاع (موافقةُ المحلّلين):\n       " + "\n       ".join(c["info"]))
own = F.REPORTS / f"{base.get('fingerprint')}.json"
if ver != "1.0":
    same = own.exists() and json.loads(own.read_text(encoding="utf-8")).get("metrics") == base.get("metrics")
    check(same, "٥ ومقاييسُ الأساس هي تقريرُ بصمته نفسُه — قِيس قبل النشر وطابقه الإنتاج")

# المقارنةُ نفسُها تُسقط أساساً أضعف — بحالةٍ معروفةٍ سلفاً
weak = dict(base.get("metrics") or {}, coverage=(base["metrics"]["coverage"] - 0.05))
w, _ = F.compare(base.get("metrics") or {}, weak)
check(any(x.startswith("coverage") for x in w), "٦ وأساسٌ أضعفُ تغطيةً يُكشف تراجعُه")

# ‏D707 — سلوكاً على سلسلةٍ مصطنعة: سابقٌ جُمّد يوماً مضى بلا مقاييس نتيجة، وشاهدُه مَقيساً يومَ تقرير الجديد
import tempfile  # noqa: E402
tmp = pathlib.Path(tempfile.mkdtemp(prefix="sp-chain-"))
P, N = "aaaaaaaaaaaa", "bbbbbbbbbbbb"
old_day = {"coverage": 0.89, "median_dev": 0.13, "verdict": {"٤ المرجع": True, "١ التغطية": True}}
witness = {"coverage": 0.89, "median_dev": 0.16, "o_ic12": 0.03, "verdict": {"٤ المرجع": True, "١ التغطية": True}}
new = {"coverage": 0.95, "median_dev": 0.23, "o_ic12": 0.23, "verdict": {"٤ المرجع": False, "١ التغطية": True}}
(tmp / f"{P}.json").write_text(json.dumps({"fingerprint": P, "measured_at": "2026-10-10", "metrics": old_day}), encoding="utf-8")
(tmp / f"{N}.json").write_text(json.dumps({"fingerprint": N, "measured_at": "2026-10-14", "metrics": new}), encoding="utf-8")
nb = {"version": "x", "fingerprint": N, "measured_at": "2026-10-14", "metrics": new, "sources": {"previous": f"السابق {P}"}}
(tmp / f"{P}.control.json").write_text(json.dumps({"fingerprint": P, "measured_at": "2026-10-14", "metrics": witness}), encoding="utf-8")
a = chain(nb, tmp)
check(not a.get("worse") and any(x.startswith("o_ic12") for x in a.get("better") or []) and "2026-10-14" in a.get("how", ""),
      "٧ السابقُ مَقيساً يومَ تقرير الجديد هو المرجع (‏D692)، والنتيجةُ هي الحَكَم وموافقةُ المحلّلين للاطّلاع (‏D700)",
      f"{a.get('how')} · تراجع {a.get('worse')} · تفوّق {a.get('better')}")
(tmp / f"{P}.control.json").write_text(json.dumps({"fingerprint": P, "measured_at": "2026-10-12", "metrics": witness}), encoding="utf-8")
b = chain(nb, tmp)
check(any(x.startswith("median_dev") for x in b.get("worse") or []),
      "٨ ولا شاهدَ من يومٍ آخر: بلا قياسٍ في اليوم نفسِه يبقى المرجعُ يومَ التجميد، وموافقةُ المحلّلين تُحاسَب فيه",
      f"{b.get('how')} · تراجع {b.get('worse')}")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
