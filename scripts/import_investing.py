"""استيرادُ القوائم المالية من ملفّات «إنفستنغ» التي تصدّرها بيدك.

## الاستعمال

    # ١) عرضٌ بلا كتابة — يقول ماذا فهم وماذا لم يفهم
    python scripts/import_investing.py ~/investing --dry-run

    # ٢) الكتابةُ بعد أن تطمئنّ
    python scripts/import_investing.py ~/investing

يقبل `.csv` و`.xlsx` (إن توفّرت openpyxl)، ملفاً واحداً أو مجلّداً.

## كيف يعرف الرمز والسنة

الرمزُ من اسم الملفّ (‏`2222.csv` · `2222_income.csv` · `tasi-2222.xlsx`)
أو من عمودٍ اسمُه رمز/‏symbol/‏ticker. والسنواتُ من رؤوس الأعمدة، والبنودُ
من العمود الأوّل — وهي بنيةُ تصدير القوائم المعتادة (بندٌ في كلّ سطر،
سنةٌ في كلّ عمود). ويقبل المقلوب أيضاً (سنةٌ في كلّ سطر).

## قاعدتان لا تُخترقان

  · **ياهو هو المزوّد.** هذا المخزنُ مُكمِّل: يملأ الفراغَ ولا يستبدل
    رقماً من ياهو أبداً (‏`_merge_supplement`).
  · **لا يُخمَّن بند.** ما لم يُطابق اسمُه الخريطةَ يُعرض في «لم يُفهَم»
    ولا يُحقن. وسطرٌ بلا سنةٍ صريحة يُهمَل.
"""

from __future__ import annotations

import csv
import json
import os
import re
import sys
import tempfile
from collections import defaultdict

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in ("/app", os.path.join(_ROOT, "backend"), _ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ── خريطةُ البنود ───────────────────────────────────────────────────────
# المفتاحُ اسمُنا الداخليّ، والقيمةُ أسماءٌ تُطابَق بعد التبسيط (حروفٌ
# صغيرة، بلا رموزٍ ولا مسافات). وأسماءُ «إنفستنغ» الإنجليزية والعربية
# معاً — وما لم يُطابق يُعلَن ولا يُخمَّن.
FIELDS: dict[str, tuple[str, ...]] = {
    "revenue": ("totalrevenue", "revenue", "netsales", "sales",
                "الإيرادات", "إجماليالإيرادات", "المبيعات"),
    "gross_profit": ("grossprofit", "مجملالربح", "إجماليالربح"),
    "operating_income": ("operatingincome", "operatingprofit",
                         "الربحالتشغيلي", "الدخلالتشغيلي"),
    "net_income": ("netincome", "netincometocommon", "netprofit",
                   "صافيالدخل", "صافيالربح"),
    "eps": ("dilutedepsexcludingextraordinaryitems", "dilutedeps",
            "basiceps", "epsdiluted", "ربحيةالسهم", "العائدعلىالسهم"),
    "total_assets": ("totalassets", "إجماليالأصول", "مجموعالأصول"),
    "total_liabilities": ("totalliabilities", "إجماليالالتزامات",
                          "مجموعالالتزامات"),
    "equity": ("totalequity", "totalstockholdersequity", "stockholdersequity",
               "shareholdersequity", "حقوقالملكية", "حقوقالمساهمين",
               "إجماليحقوقالملكية"),
    "total_debt": ("totaldebt", "totallongtermdebt", "longtermdebt",
                   "إجماليالديون", "الديون"),
    "ending_cash": ("cashandequivalents", "cashandshortterminvestments",
                    "cash", "النقدومايعادله", "النقدية"),
    "current_assets": ("totalcurrentassets", "الأصولالمتداولة"),
    "current_liabilities": ("totalcurrentliabilities", "الالتزاماتالمتداولة"),
    "inventory": ("totalinventory", "inventory", "المخزون"),
    "operating_cash_flow": ("cashfromoperatingactivities",
                            "netcashprovidedbyoperatingactivities",
                            "operatingcashflow", "التدفقالنقديالتشغيلي",
                            "النقدمنالأنشطةالتشغيلية"),
    "capex": ("capitalexpenditures", "capex", "النفقاتالرأسمالية"),
    "depreciation": ("depreciationdepletion", "depreciationandamortization",
                     "depreciationamortization", "الاستهلاكوالإطفاء"),
    "interest_expense": ("interestexpense", "interestexpensenetofinterest",
                         "مصروفالفوائد", "تكاليفالتمويل"),
    "dividends_paid": ("totalcashdividendspaid", "dividendspaid",
                       "التوزيعاتالنقدية", "الأرباحالموزعة"),
    "shares_outstanding": ("totalcommonsharesoutstanding",
                           "sharesoutstanding", "عددالأسهم"),
}

# مقياسُ الأرقام: كثيرٌ من التصديرات بالملايين
SCALE_HINTS = (("inmillions", 1e6), ("بالملايين", 1e6),
               ("inthousands", 1e3), ("بالآلاف", 1e3),
               ("inbillions", 1e9), ("بالمليارات", 1e9))


def _norm(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"[ً-ْـ]", "", s)      # تشكيلٌ وتطويل
    s = s.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    return re.sub(r"[^0-9a-zء-ي]", "", s)


_LOOKUP = {}
for _k, _names in FIELDS.items():
    for _n in _names:
        _LOOKUP[_norm(_n)] = _k


def _num(v) -> float | None:
    if v is None:
        return None
    s = str(v).strip().replace(",", "").replace("٬", "")
    if not s or s in ("-", "—", "--", "N/A", "n/a"):
        return None
    neg = s.startswith("(") and s.endswith(")")
    if neg:
        s = s[1:-1]
    mult = 1.0
    for suf, m in (("B", 1e9), ("M", 1e6), ("K", 1e3)):
        if s.upper().endswith(suf):
            s, mult = s[:-1], m
            break
    try:
        x = float(s) * mult
    except ValueError:
        return None
    return -x if neg else x


_YEAR = re.compile(r"(19|20)\d{2}")


def _year_of(text: str) -> int | None:
    m = _YEAR.search(str(text or ""))
    if not m:
        return None
    y = int(m.group(0))
    return y if 1990 <= y <= 2100 else None


def _symbol_of(name: str, rows: list[list[str]]) -> str | None:
    m = re.search(r"(?<!\d)(\d{4})(?!\d)", os.path.basename(name))
    if m:
        return m.group(1)
    for row in rows[:6]:
        for i, cell in enumerate(row):
            if _norm(cell) in ("رمز", "symbol", "ticker", "الرمز"):
                for r2 in rows[:8]:
                    if len(r2) > i:
                        m2 = re.search(r"(?<!\d)(\d{4})(?!\d)", str(r2[i]))
                        if m2:
                            return m2.group(1)
    return None


def _read(path: str) -> list[list[str]]:
    if path.lower().endswith((".xlsx", ".xlsm")):
        try:
            from openpyxl import load_workbook
        except ImportError:
            return []
        wb = load_workbook(path, read_only=True, data_only=True)
        out = []
        for ws in wb.worksheets:
            for r in ws.iter_rows(values_only=True):
                out.append(["" if c is None else str(c) for c in r])
        return out
    for enc in ("utf-8-sig", "utf-8", "cp1256"):
        try:
            with open(path, encoding=enc, newline="") as fh:
                sample = fh.read(4096)
                fh.seek(0)
                try:
                    d = csv.Sniffer().sniff(sample, delimiters=",;\t")
                except csv.Error:
                    d = csv.excel
                return [list(r) for r in csv.reader(fh, d)]
        except (UnicodeDecodeError, OSError):
            continue
    return []


def parse(path: str) -> tuple[str | None, dict[int, dict], list[str]]:
    """يعيد (الرمز، {سنة: {حقل: قيمة}}، بنودٌ لم تُفهَم)."""
    rows = _read(path)
    if not rows:
        return None, {}, []
    sym = _symbol_of(path, rows)

    scale = 1.0
    blob = _norm(" ".join(" ".join(r) for r in rows[:5]))
    for hint, m in SCALE_HINTS:
        if _norm(hint) in blob:
            scale = m
            break

    # اتّجاهُ الجدول: سنواتٌ في الرؤوس (المعتاد) أم في العمود الأوّل
    best_i, best_years = None, {}
    for i, r in enumerate(rows[:12]):
        ys = {j: _year_of(c) for j, c in enumerate(r) if _year_of(c)}
        if len(ys) > len(best_years):
            best_i, best_years = i, ys

    out: dict[int, dict] = defaultdict(dict)
    unknown: list[str] = []
    if best_years:
        for r in rows[(best_i or 0) + 1:]:
            if not r:
                continue
            key = _LOOKUP.get(_norm(r[0]))
            if key is None:
                if _norm(r[0]) and not _year_of(r[0]):
                    unknown.append(str(r[0]).strip()[:48])
                continue
            for j, yr in best_years.items():
                if len(r) > j:
                    v = _num(r[j])
                    if v is not None:
                        out[yr][key] = v * (scale if abs(v) < 1e7 else 1.0)
    return sym, dict(out), sorted(set(unknown))


def main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith("-")]
    dry = "--dry-run" in argv
    if not args:
        print(__doc__)
        return 2
    target = os.path.expanduser(args[0])
    files = ([os.path.join(target, f) for f in sorted(os.listdir(target))
              if f.lower().endswith((".csv", ".xlsx", ".xlsm"))]
             if os.path.isdir(target) else [target])
    if not files:
        print(f"✖ لا ملفّاتٍ في {target}")
        return 2

    from app.services import investing_store

    companies: dict[str, list[dict]] = {}
    unknown_all: dict[str, int] = defaultdict(int)
    skipped: list[str] = []

    for f in files:
        sym, years, unknown = parse(f)
        for u in unknown:
            unknown_all[u] += 1
        if not sym:
            skipped.append(f"{os.path.basename(f)}: لا رمزَ في الاسم ولا عمود")
            continue
        if not years:
            skipped.append(f"{os.path.basename(f)}: لا سنواتٍ مفهومة")
            continue
        rows = companies.setdefault(sym, [])
        by_year = {r["year"]: r for r in rows}
        for yr, vals in years.items():
            row = by_year.setdefault(yr, {"year": yr})
            row.update(vals)
            if row not in rows:
                rows.append(row)

    print("═" * 66)
    print("  استيرادُ قوائم «إنفستنغ»" + ("  (عرضٌ بلا كتابة)" if dry else ""))
    print("═" * 66)
    print(f"  ملفّات {len(files)} · شركات {len(companies)} · "
          f"صفوف {sum(len(v) for v in companies.values())}")
    cov: dict[str, int] = defaultdict(int)
    for rows in companies.values():
        for r in rows:
            for k in r:
                if k != "year":
                    cov[k] += 1
    print(f"\n  البنودُ المفهومة ({len(cov)}/{len(FIELDS)}):")
    for k in FIELDS:
        n = cov.get(k, 0)
        print(f"    {'✔' if n else '·'} {k:24} {n or 'لم يصل'}")
    if unknown_all:
        print(f"\n  بنودٌ لم تُفهَم ({len(unknown_all)}) — تُهمَل ولا تُخمَّن:")
        for u, n in sorted(unknown_all.items(), key=lambda x: -x[1])[:15]:
            print(f"    · {u}   ×{n}")
    if skipped:
        print(f"\n  ملفّاتٌ تُخُطّيت ({len(skipped)}):")
        for x in skipped[:10]:
            print(f"    · {x}")

    if dry:
        print("\n  عرضٌ فقط — لم يُكتب شيء. احذف --dry-run للكتابة.")
        return 0
    if not companies:
        print("\n  ✖ لا شيءَ يُكتب.")
        return 1

    from datetime import datetime, timezone
    payload = {"source": "investing.com (تصديرٌ يدويٌّ من حساب المالك)",
               "imported_at": datetime.now(timezone.utc).isoformat(),
               "files": len(files), "companies": companies}
    p = investing_store.path()
    os.makedirs(os.path.dirname(p), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(p), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False)
    os.replace(tmp, p)
    print(f"\n  ✔ كُتب {p}")
    print(f"    شركات {investing_store.reload()} · "
          f"{investing_store.census()}")
    print("\n  ياهو يبقى المزوّد — هذا يملأ الفراغَ ولا يستبدل رقماً منه.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
