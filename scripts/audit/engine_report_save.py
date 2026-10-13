#!/usr/bin/env python3
"""يحفظ مقاييسَ البوابة لبصمة المحرّكات الحالية (‏D635).

    python3 scripts/audit/engine_report_save.py <مخرَج engine_gate> [<مخرَج engines_gate_v1>] [--baseline 1.0]

بلا `--baseline`: يكتب `engine_reports/<البصمة>.json` — تقريرُ إصدارٍ مقترَح يحكم فيه حارسُ التجميد.
ومع `--control`: شاهدُ الأساس المجمَّد في يوم المرشَّح (‏D692) — ومن مهمّة `candidate_ab` في الجولة نفسِها (‏D696).
ومع `--baseline <الإصدار>`: يكتب خطَّ الأساس المجمَّد `engine_baseline.json` (عند التجميد وحده)."""
import datetime as dt, json, pathlib, re, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from engine_freeze_d635 import BASE, REPORTS, fingerprint   # noqa: E402


def main() -> int:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 2
    # ‏D639: مخرَجا البوابتين (السعر العادل · المحرّكات ٢–٥) يُدمجان في تقريرٍ واحد، والأحكامُ تُجمع
    # ‏D676: «--accept مقياس=أرضيّة --decision "نصُّ قرار المالك"» — تراجعٌ قَبِله المالكُ بنصّه، يُحفظ مع التقرير
    _flagv = {"--baseline", "--accept", "--decision", "--measured", "--run"}
    files = [a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or args[i - 1] not in _flagv)]
    accepted = {}
    # ‏D700: أكثرُ من قبولٍ في التقرير الواحد — كلُّ «--accept» يليه «--decision» الخاصُّ به؛ والبندُ بلا أرضيّة «اسمُه=-»
    for j, a in enumerate(args):
        if a != "--accept":
            continue
        k, fl = args[j + 1].split("=", 1)
        dec = args[j + 3] if j + 3 < len(args) and args[j + 2] == "--decision" else ""
        if not dec:
            print("--accept بلا --decision يليه: لا قبولَ بلا نصّ القرار")
            return 2
        accepted[k] = {"floor": None if fl == "-" else float(fl), "decision": dec}
    metrics: dict = {}
    measured_fps: set = set()
    for fpath in files:
        text = pathlib.Path(fpath).read_text(encoding="utf-8", errors="replace")
        # ‏D696: البوابةُ تطبع بصمةَ الشيفرة التي قاستها فعلاً — فلا يُنسب قياسٌ إلى غير شيفرته
        measured_fps |= set(re.findall(r"@@ENGINE_FP@@ ([0-9a-f]{12})", text))
        lines = [ln for ln in text.splitlines() if "@@METRICS@@" in ln]
        if not lines:
            print(f"لا سطرَ @@METRICS@@ في {fpath}")
            return 1
        m = json.loads(lines[-1].split("@@METRICS@@", 1)[1])
        verdict = {**(metrics.get("verdict") or {}), **(m.pop("verdict", None) or {})}
        metrics.update(m)
        metrics["verdict"] = verdict
    # ‏D692: يومُ القياس يومُ تشغيل البوابة على الخادم (‏--measured) لا يومُ الحفظ — فشاهدُ اليوم نفسِه لا يُختلق تاريخُه
    _measured = args[args.index("--measured") + 1] if "--measured" in args else dt.date.today().isoformat()
    if len(measured_fps) > 1:
        print(f"مخرَجاتٌ من شيفرتين ({sorted(measured_fps)}) — لا يُدمج قياسان في تقريرٍ واحد")
        return 1
    measured_fp = next(iter(measured_fps), None)
    if "--control" in args or "--addendum" in args:
        base = json.loads(BASE.read_text(encoding="utf-8")) if BASE.exists() else {}
        fp_doc = measured_fp or fingerprint()
    else:
        fp_doc = fingerprint()
        if measured_fp and measured_fp != fp_doc:
            print(f"البوابةُ قاست الشيفرةَ {measured_fp} والشجرةُ هنا {fp_doc} — التقريرُ يُحفظ لشيفرته وحدها")
            return 1
    doc = {"fingerprint": fp_doc, "measured_at": _measured, "metrics": metrics}
    if "--run" in args:
        doc["run"] = args[args.index("--run") + 1]
    if accepted:
        doc["owner_accepted"] = accepted
    if "--addendum" in args:
        # ‏D681: مقاييسُ جديدةٌ في البوابة تُقاس على شيفرة الأساس المجمَّد نفسِها — ملحقٌ بجانب تقريره لا تعديلٌ له
        REPORTS.mkdir(exist_ok=True)
        rep = REPORTS / f"{doc['fingerprint']}.json"
        if not rep.exists():
            print(f"لا تقريرَ للبصمة {doc['fingerprint']} — الملحقُ يُقاس على شيفرة إصدارٍ مقيسٍ مجمَّد")
            return 1
        have = json.loads(rep.read_text(encoding="utf-8")).get("metrics") or {}
        extra = {k: v for k, v in metrics.items() if k not in have and k != "verdict"}
        out = REPORTS / f"{doc['fingerprint']}.addendum.json"
        out.write_text(json.dumps({"fingerprint": doc["fingerprint"], "measured_at": doc["measured_at"], "metrics": extra,
                                   "note": "مقاييسُ أُضيفت للبوابة بعد التجميد وقِيست على شيفرته نفسِها"},
                                  ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"ملحقُ البصمة {doc['fingerprint']} ← {out} · {sorted(extra)}")
        return 0
    if "--control" in args:
        # ‏D692: شيفرةُ الأساس المجمَّد نفسُها مقيسةً في يوم المرشَّح — مرجعُ المقارنة على البيانات نفسِها، لا تجميدٌ جديد.
        # ‏D696: والبصمةُ بصمةُ ما قاسته البوابةُ (من الأساس المجمَّد في الجولة نفسِها) إن طبعتها — لا بصمةُ الشجرة هنا
        if doc["fingerprint"] != base.get("fingerprint"):
            print(f"البصمةُ {doc['fingerprint']} ليست بصمةَ الأساس المجمَّد {base.get('fingerprint')} — الشاهدُ يُقاس على شيفرته وحدها")
            return 1
        REPORTS.mkdir(exist_ok=True)
        out = REPORTS / f"{doc['fingerprint']}.control.json"
        out.write_text(json.dumps({**doc, "note": "شيفرةُ الأساس المجمَّد مقيسةً في يومٍ لاحق — مرجعُ مقارنة المرشَّح في يومه"},
                                  ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"شاهدُ الأساس {doc['fingerprint']} ({doc['measured_at']}) ← {out}")
        return 0
    if "--baseline" in args:
        doc["version"] = args[args.index("--baseline") + 1]
        BASE.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"خطُّ الأساس المجمَّد: الإصدار {doc['version']} · {doc['fingerprint']}")
    else:
        REPORTS.mkdir(exist_ok=True)
        out = REPORTS / f"{doc['fingerprint']}.json"
        out.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"تقريرُ البصمة {doc['fingerprint']} ← {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
