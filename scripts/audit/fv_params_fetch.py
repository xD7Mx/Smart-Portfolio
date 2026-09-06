#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# جالبُ معايير محرّك القيمة العادلة — يُشغَّل على الخادم حيث الشبكةُ مفتوحة.
#
# المحرّك يرفض العمل بمعايير مفترَضة: `risk_free_sar` فارغةٌ عمداً، والبيتا
# القطاعية معلَّمةٌ «غير موثّقة»، وملفُّ المعايير له عمرٌ أقصى. هذا السكربت
# يجلب ما يمكن جلبُه **بمصدره وتاريخه**، ولا يخترع ما لا يجده.
#
#   docker exec sp_backend python /app/scripts/audit/fv_params_fetch.py
#
# يطبع ما وجد، ويكتب `reports/fv_params_raw.json`. ولا يعدّل ملفَّ المعايير —
# التوثيقُ قرارٌ يُتَّخذ بعد النظر في الأرقام، لا أثرٌ جانبيٌّ لجلبها.
# ─────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import datetime as dt
import json
import pathlib
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "reports" / "fv_params_raw.json"

CRP = "https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/ctryprem.html"
BETA_EM = "https://pages.stern.nyu.edu/~adamodar/pc/datasets/betaemerg.html"
UA = {"User-Agent": "Mozilla/5.0 (fair-value-params-fetch)"}


def get(url: str) -> str | None:
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=45) as r:
            return r.read().decode("utf-8", "replace")
    except Exception as e:                                        # noqa: BLE001
        print(f"  ✖ تعذّر الجلب: {type(e).__name__}: {e}")
        return None


def tables(html: str):
    """جداولُ الصفحة صفوفاً نصّية — بلا اعتمادٍ على pandas/lxml."""
    import re
    from html import unescape
    out = []
    for tbl in re.findall(r"<table.*?</table>", html, re.S | re.I):
        rows = []
        for tr in re.findall(r"<tr.*?</tr>", tbl, re.S | re.I):
            cells = [unescape(re.sub(r"<[^>]+>", "", td)).replace("\xa0", " ").strip()
                     for td in re.findall(r"<t[dh].*?</t[dh]>", tr, re.S | re.I)]
            if any(cells):
                rows.append(cells)
        if rows:
            out.append(rows)
    return out


def main() -> int:
    found: dict = {"fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}

    # ── ١ · علاوةُ المخاطر القُطرية: صفُّ السعودية بلفظه ──────────────
    print("\n[١] علاوةُ المخاطر القُطرية — داموداران")
    print(f"    {CRP}")
    html = get(CRP)
    if html:
        rows = [r for t in tables(html) for r in t]
        hits = [r for r in rows if any("saudi" in c.lower() for c in r)]
        head = next((r for t in tables(html) for r in t[:3]
                     if any("Country" == c.strip() for c in r)), None)
        found["crp_header"] = head
        found["crp_saudi_rows"] = hits
        print(f"    الترويسة: {head}")
        for r in hits:
            print(f"    صفّ: {r}")
        if not hits:
            print("    ✖ لم يوجد صفٌّ للسعودية — تغيّر شكلُ الصفحة؟ افتحها بنفسك.")

    # ── ٢ · البيتا القطاعية للأسواق الناشئة ────────────────────────────
    print("\n[٢] البيتا القطاعية — الأسواق الناشئة")
    print(f"    {BETA_EM}")
    html = get(BETA_EM)
    if html:
        rows = [r for t in tables(html) for r in t]
        found["beta_rows"] = rows[:250]
        print(f"    صفوف: {len(rows)} — أوّلُها: {rows[0] if rows else '—'}")
        print("    (الجدولُ كاملاً في التقرير؛ المطابقةُ بقطاعات تداول تُبنى بعد النظر فيه)")

    # ── ٣ · المعدّلُ الخالي من المخاطر بالريال ─────────────────────────
    # لا مصدرَ عامٌّ موثوقٌ يُقرأ آلياً لمنحنى العائد السياديّ بالريال.
    # يُقرأ يدوياً من مركز إدارة الدين أو من اشتراك المالك، ويُدوَّن بتاريخه.
    print("\n[٣] المعدّل الخالي من المخاطر بالريال — يدويّ")
    print("    عائدُ الصكوك/السندات السيادية السعودية العشرية **بالريال**.")
    print("    المصادر: مركز إدارة الدين (ndmc.gov.sa) · منحنى تداول للصكوك")
    print("    · أو اشتراكُك في investing.com. دوّن الرقمَ وتاريخَه.")
    found["risk_free_sar"] = None

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(found, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nالتقرير الخام: {OUT}")
    print("لا شيءَ وُثّق بعد — التوثيقُ يقع في market_params.json بعد النظر في هذه الأرقام.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
