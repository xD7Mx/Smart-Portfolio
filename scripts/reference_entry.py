"""إدخالُ مراجع InvestingPro — قالبٌ ثمّ استيراد.

## الاستعمال

    # ١) يُنشئ قالباً فارغاً بشركاتٍ متنوّعةِ القطاعات
    python scripts/reference_entry.py --template > /home/ubuntu/ref.csv

    # ٢) تملؤه بيدك من InvestingPro، ثمّ:
    python scripts/reference_entry.py /home/ubuntu/ref.csv --dry-run
    python scripts/reference_entry.py /home/ubuntu/ref.csv

## شكلُ الملفّ

    الرمز,درجة السلامة,القيمة العادلة
    2222,3.2,31.30
    1120,,
    ...

  · **درجةُ السلامة** كما يعرضها الموقع (‏0–5 أو 0–100 — يُكتشف المقياس).
  · **القيمةُ العادلة** بالريال.
  · اتركِ الخانةَ فارغةً لما لم تجده. الفراغُ يبقى فراغاً ولا يُخمَّن.

هذه أرقامُ مرجعٍ للمعايرة: لا تدخل درجةَ الحوكمة ولا تُعرض للمستخدم.
"""

from __future__ import annotations

import csv
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in ("/app", os.path.join(_ROOT, "backend"), _ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

HEADER = ["الرمز", "درجة السلامة", "القيمة العادلة"]


def _template() -> int:
    """عيّنةٌ متنوّعةُ القطاعات — لا الأكبرَ حجماً وحدها.

    المعايرةُ على البنوك وحدها تقول إن المحرّك جيّدٌ للبنوك. فتُؤخذ من
    كلّ قطاعٍ شركةٌ أو اثنتان حتى يُقاس المحرّكُ حيث يُستعمل.
    """
    from app.data.market_universe import MARKET_UNIVERSE
    from app.data import universe as uni
    from app.data.saudi_directory import name_of
    from collections import defaultdict
    MAIN = uni.main_market(MARKET_UNIVERSE)
    by_sec = defaultdict(list)
    for s, m in MAIN.items():
        if m.get("sector"):
            by_sec[m["sector"]].append(s)
    w = csv.writer(sys.stdout)
    w.writerow(HEADER + ["اسم الشركة (للتسهيل — يُتجاهَل)", "القطاع"])
    for sec, syms in sorted(by_sec.items(), key=lambda kv: -len(kv[1])):
        for s in sorted(syms)[:2]:            # اثنتان من كلّ قطاع
            w.writerow([s, "", "", name_of(s) or "", sec])
    return 0


def main(argv: list[str]) -> int:
    if "--template" in argv:
        return _template()
    args = [a for a in argv if not a.startswith("-")]
    if not args:
        print(__doc__)
        return 2
    dry = "--dry-run" in argv
    path = os.path.expanduser(args[0])

    rows: dict[str, dict] = {}
    blank, bad = 0, []
    with open(path, encoding="utf-8-sig", newline="") as fh:
        for i, r in enumerate(csv.reader(fh), 1):
            if not r or not (r[0] or "").strip():
                continue
            sym = (r[0] or "").strip().split(".")[0]
            if not sym.isdigit() or len(sym) != 4:
                if i > 1:
                    bad.append(f"سطر {i}: «{r[0][:20]}» ليس رمزاً رباعياً")
                continue

            def num(idx):
                if len(r) <= idx:
                    return None
                s = (r[idx] or "").strip().replace(",", "")
                try:
                    return float(s) if s else None
                except ValueError:
                    return None

            h, fv = num(1), num(2)
            if h is None and fv is None:
                blank += 1
                continue
            rec = {}
            if h is not None:
                rec["health_raw"] = h
                # المقياسُ يُكتشف ولا يُفترض: الموقعُ يعرضها ‎0–5 أحياناً
                # و‎0–100 أحياناً. وتحويلٌ خاطئٌ يفسد المقارنةَ كلَّها.
                rec["health_100"] = round(h * 20, 1) if h <= 5 else round(h, 1)
            if fv is not None:
                rec["fair_value"] = fv
            rows[sym] = rec

    print("═" * 60)
    print("  مراجعُ المعايرة" + ("  (عرضٌ بلا كتابة)" if dry else ""))
    print("═" * 60)
    nh = sum(1 for v in rows.values() if "health_100" in v)
    nf = sum(1 for v in rows.values() if "fair_value" in v)
    print(f"  شركاتٌ مُدخَلة {len(rows)} · درجةُ سلامة {nh} · قيمةٌ عادلة {nf}")
    if blank:
        print(f"  صفوفٌ فارغة (تُهمَل) {blank}")
    for b in bad[:6]:
        print(f"  ✖ {b}")
    scales = {("0–5" if v.get("health_raw", 0) <= 5 else "0–100")
              for v in rows.values() if "health_raw" in v}
    if scales:
        print(f"  مقياسُ الدرجة المكتشَف: {' و '.join(sorted(scales))}"
              + ("   ⚠ مقياسان مختلطان — راجِع الملفّ"
                 if len(scales) > 1 else ""))
    if dry:
        print("\n  عرضٌ فقط — لم يُكتب شيء.")
        return 0
    if not rows:
        print("\n  ✖ لا شيءَ يُكتب.")
        return 1
    from app.services import reference_scores
    p = reference_scores.save(rows)
    print(f"\n  ✔ كُتب {p}")
    print("  مرجعٌ للمعايرة — لا يدخل درجةَ الحوكمة ولا يُعرض للمستخدم.")
    print("  التالي:  python scripts/audit/reference_compare.py")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
