#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# D263 — قوائمُ رسميةٌ مدقَّقةٌ تتقدّم المزوّد، وبندٌ لا يُخمَّن.
#
# الدرجةُ والسعرُ العادل يُبنيان على القوائم، وكانت من ياهو: ناقصةً،
# ومحدودةَ الحصّة، وبلا ربعيٍّ لأكثر رموز السوق. وقياسُ المصادر ردَّ
# تبويبَ قوائم «تداول» (متجمّدٌ عند ‎2023) وصفحاتِ «أرقام» (جافاسكربت)،
# وأبقى ملفّاتِ **XBRL** المرفقةَ بكلّ إفصاح: مدقَّقةٌ · موحَّدةٌ ·
# بتصنيف IFRS · مؤرَّخةٌ بفترتها وإيداعها.
#
# وخطرُها في المطابقة: بندٌ يُملأ بأقربِ اسمٍ شبيهٍ يجعل «إجمالي
# الالتزامات» حقوقَ ملكية — والدرجةُ تُبنى عليه فيصير الخطأُ حكماً على
# شركة. فيُقاس السلوكُ بملفٍّ مموَّهٍ على شكل الملفّ الرسميّ المقيس:
#   ٠· البنودُ تُقرأ بأسمائها الرسمية كما وردت
#   ١· ووحدةُ التقريب تُقرأ لا تُفترَض (‏Thousands ⇒ ×1000)
#   ٢· والسالبُ بين قوسين سالب
#   ٣· ونوعُ الفترة من الملفّ نفسِه (سنويٌّ/ربعيّ) لا من تاريخه
#   ٤· والمديونيةُ تُشتقّ من بندين مقروءين لا تُنسَخ
#   ٥· وبندٌ لم يُعرَف يُترك — لا يُملأ بشبيهه
#   ٦· وعمودٌ بلا بندٍ واحدٍ ليس فترة
#   ٧· والبابُ الواحد يُقدّم الرسميَّ على المزوّد، وبغيابه لا ينكسر شيء
#   ٨· وإيداعٌ شائخٌ لا يُقرأ «أحدثَ قوائم»
# ─────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import os as _os
import tempfile as _tf

_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX

import asyncio  # noqa: E402
import datetime as _dt  # noqa: E402
import pathlib  # noqa: E402
import sys  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")

fail = 0


def check(ok: bool, label: str, detail: str = "") -> None:
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {detail}" if detail else ""))


from app.services import tadawul_xbrl as xb  # noqa: E402


def row(label, *vals):
    return "<tr><td>" + label + "</td>" + "".join(
        f"<td>{v}</td>" for v in vals) + "</tr>"


# ملفٌّ على شكل الملفّ الرسميّ المقيس (سابك · 2010) بنصّ بنوده.
DOC = "<table>" + "".join([
    row("Period covered by financial statements", "Annual"),
    row("Status of report", "Audited"),
    row("Level of rounding used in financial statements", "Thousands"),
    row("Start Date", "2025-01-01", "2024-01-01"),
    row("End Date", "2025-12-31", "2024-12-31"),
    row("Total assets", "318,438,777", "295,468,550"),
    row("Total liabilities", "106,605,479", "101,231,425"),
    row("Total equity", "211,833,298", "194,237,125"),
    row("Total revenue", "174,883,126", "116,949,287"),
    row("Finance costs", "2,257,224", "1,860,667", "32"),
    row("Profit (loss) for period", "30,501,771", "(1,256,229)"),
    row("Total basic earnings (loss) per share", "7.69", "0.02"),
    row("Cash flows from (used in) operating activities", "40,000,000", "30,000,000"),
    row("Purchase of property, plant and equipment", "12,000,000", "9,000,000"),
    row("Profit (loss) before zakat and income tax from continuing operations",
        "34,087,964", "3,277,257"),
    row("Current borrowings", "5,000,000", "4,000,000"),
    row("Non-current borrowings", "60,000,000", "58,000,000"),
    row("Current lease liabilities", "1,000,000", "900,000"),
    row("Number of shares outstanding", "3,000,000,000", "3,000,000,000"),
    row("Retained earnings (accumulated losses)", "27,794,542", "15,071,361"),
]) + "</table>"

got = xb.parse(DOC)
P = got.get("periods") or []
last = P[-1] if P else {}

check(len(P) == 2 and last.get("as_of") == "2025-12-31",
      "٠ الفتراتُ تُقرأ من صفَّي التاريخ، والأحدثُ آخِراً", str([p["as_of"] for p in P]))
check(last.get("revenue") == 174_883_126_000.0,
      "١ ووحدةُ التقريب تُقرأ لا تُفترَض — Thousands ⇒ ×1000",
      f"{last.get('revenue'):,}" if last.get("revenue") else "—")
check(P[0].get("net_income") == -1_256_229_000.0,
      "٢ والسالبُ بين قوسين سالب", str(P[0].get("net_income")))
check((got.get("kind") or "").lower().startswith("annual")
      and (got.get("audited") or "") == "Audited",
      "٣ ونوعُ الفترة وحالُ التدقيق من الملفّ نفسِه",
      f"{got.get('kind')} · {got.get('audited')}")
check(last.get("debt_ratio") == round(106_605_479 / 318_438_777 * 100, 2),
      "٤ والمديونيةُ تُشتقّ من بندين مقروءين", str(last.get("debt_ratio")))
check(last.get("free_cash_flow") == 28_000_000_000.0,
      "٤ب والتدفّقُ الحرّ = التشغيليُّ − الرأسماليّ", str(last.get("free_cash_flow")))
check("retained_earnings" not in last and "equity" in last,
      "٥ وبندٌ لم يُعرَف يُترك — لا يُملأ بشبيهه")
check(last.get("eps") == 7.69, "٥ب وربحيةُ السهم لا تُضرَب في وحدة التقريب",
      str(last.get("eps")))

# ── ٥ج · بنودُ المحرّك الثلاثة التي كانت تخصم الثقة ─────────────────────
check(last.get("ebit") == round((34_087_964 + 2_257_224) * 1000, 2),
      "٥ج والربحُ التشغيليُّ يُشتقّ: قبلَ الزكاة + تكلفةُ التمويل",
      f"{last.get('ebit'):,}" if last.get("ebit") else "—")
check(last.get("total_debt") == round((5_000_000 + 60_000_000 + 1_000_000) * 1000, 2),
      "٥د وإجماليُّ الدَّين مجموعُ ما قُرئ من قروضٍ وإيجارات",
      f"{last.get('total_debt'):,}" if last.get("total_debt") else "—")
check(last.get("shares_outstanding") == 3_000_000_000.0,
      "٥ه وعددُ الأسهم عددٌ لا مالٌ — لا يُضرَب في وحدة التقريب",
      str(last.get("shares_outstanding")))

# وبالاتّجاه المعاكس: غيابُ أحدِ طرفَي الاشتقاق يمنعه ولا يُقدَّر بنصفه.
half = "<table>" + "".join([
    row("Level of rounding used in financial statements", "Thousands"),
    row("End Date", "2025-12-31"),
    row("Profit (loss) before zakat and income tax from continuing operations", "100"),
    row("Total revenue", "500"),
]) + "</table>"
hp = (xb.parse(half).get("periods") or [{}])[-1]
check("ebit" not in hp and "total_debt" not in hp,
      "٥و وغيابُ طرفٍ يمنع الاشتقاق — لا يُقدَّر بنصف بيان", str(sorted(hp))[:80])

# ── ٦ · عمودٌ بلا بندٍ واحدٍ ليس فترة ────────────────────────────────────
bare = "<table>" + row("End Date", "2025-12-31") + row("Note No.", "7") + "</table>"
check(not (xb.parse(bare).get("periods") or []),
      "٦ عمودٌ بلا بندٍ مفهومٍ ليس فترة")
check(xb.parse("<html>لا جدول</html>") == {},
      "٦ب وملفٌّ بلا جدولٍ يعود فارغاً لا مختلَقاً")

# ── ٧ · البابُ الواحد: الرسميُّ يتقدّم المزوّد ───────────────────────────
from app.services.market_data import MarketDataService  # noqa: E402


class _FakeYahoo:
    async def get_financials(self, symbol, allow_supplement=True):
        return {"symbol": symbol, "periods": [{"year": 2024, "revenue": 1.0}],
                "source": "ياهو"}

    async def get_quarterly_financials(self, symbol):
        return {"symbol": symbol, "periods": [{"year": 2024}], "source": "ياهو"}


svc = MarketDataService()
svc._yahoo = lambda: _FakeYahoo()                                # type: ignore[assignment]

out = asyncio.run(svc.get_financials("2010.SR"))
check((out or {}).get("source") == "ياهو",
      "٧ بلا قوائمَ رسميةٍ يعمل المزوّدُ كما كان — لا انكسار",
      str((out or {}).get("source")))

xb.save_symbol("2010", {"annual": P, "quarterly": [{"as_of": "2026-03-31",
                                                    "year": 2026, "revenue": 5.0}],
                        "as_of": _dt.date.today().isoformat()})
out = asyncio.run(svc.get_financials("2010.SR"))
# ══ والعقدُ تغيّر بأمر المالك: تُكمَّل لا تُنسَخ ══ (D336)
# كان الشرطُ «الفتراتُ **نفسُ الكائن**» (‏`periods == P`)، وطبقةُ الإكمال
# تُضيف إليها حقولاً مشتقّةً و`field_sources`. فالشرطُ الصحيح: المصدرُ
# الرسميُّ يتقدّم، و**كلُّ قيمةٍ منشورةٍ تبقى كما وردت بالحرف**،
# والزيادةُ مسموحةٌ موسومةً بمصدرها. ومقارنةُ الهويّة كانت تحرس
# «لا يُمَسّ المنشور» فصارت تحرسه بالمعنى لا بالشكل.
_got = (out or {}).get("periods") or []
_kept = (len(_got) == len(P)
         and all(all(_g.get(k) == v for k, v in _p.items())
                 for _p, _g in zip(P, _got)))
check((out or {}).get("source") == "تداول — XBRL" and _kept,
      "٧ب ومع الرسميّ يتقدّم ويُعلَن مصدرُه، وقيمُه تبقى كما وردت",
      str((out or {}).get("source")))
check(all(isinstance(_g.get("field_sources"), dict) for _g in _got),
      "٧ج وكلُّ فترةٍ تحمل مصادرَ حقولها — منشورٌ ومشتقٌّ ومكمَّل",
      str((_got[0] if _got else {}).get("field_sources"))[:80])
outq = asyncio.run(svc.get_quarterly_financials("2010.SR"))
check((outq or {}).get("source") == "تداول — XBRL"
      and len((outq or {}).get("periods") or []) == 1,
      "٧د والربعيُّ كذلك — وياهو آخرُ الطبقات لا أوّلُها")

# ── ٨ · إيداعٌ شائخ ─────────────────────────────────────────────────────
old = (_dt.date.today() - _dt.timedelta(days=xb.MAX_AGE_DAYS + 5)).isoformat()
xb.save_symbol("2010", {"annual": P, "quarterly": [], "as_of": old})
check(xb.for_symbol("2010") == [],
      f"٨ وقراءةٌ أقدمُ من {xb.MAX_AGE_DAYS} يوماً لا تُقرأ «أحدثَ قوائم»")
out = asyncio.run(svc.get_financials("2010.SR"))
check((out or {}).get("source") == "ياهو",
      "٨ب فيعود البابُ إلى الطبقة التالية", str((out or {}).get("source")))

# ── ٩ · أسماءٌ منقولةٌ بالحرف من ملفّات المالك (D344) ────────────────────
# قِيس على خادمه أن `interest_expense` يغيب في ٣٤ ورقةً من ٩٠ ومعه
# `ebit` — وفي الملفّات أسماءٌ منشورةٌ لم تُطابَق. والأسماءُ أدناه
# **نصُّ المخرَج** لا صياغتي، وقِيمُها من الملفّات المقيسة نفسِها. فلو
# غُيِّر حرفٌ في الخريطة أو حُذف اسمٌ احمرَّ هذا الفحصُ فوراً.
_LBL = """<table>
<tr><td>Level of rounding used in financial statements</td><td>Thousands</td></tr>
<tr><td>End Date</td><td>2026-06-30</td></tr>
<tr><td>Profit (loss) from continuing operations before zakat and income tax</td><td>2,982,516</td></tr>
<tr><td>Adjustments for finance costs</td><td>11,984</td></tr>
<tr><td>Debt securities, term loan, borrowings and sukuk in issue</td><td>47,583,268</td></tr>
</table>"""
_LP = (xb.parse(_LBL).get("periods") or [{}])[0]
check(_LP.get("pretax_income") == 2_982_516_000.0,
      "٩ «قبل الزكاة» بترتيب كلماتِ ملفّات البنوك — اسمٌ لا معنى",
      str(_LP.get("pretax_income")))
check(_LP.get("interest_expense") == 11_984_000.0,
      "٩ب وتكلفةُ التمويل من صفّ التسوية المنشور — لا تبقى غائبة",
      str(_LP.get("interest_expense")))
check(_LP.get("ebit") == 2_994_500_000.0,
      "٩ج فيقوم الربحُ التشغيليُّ الذي كان يسقط بسقوطها",
      str(_LP.get("ebit")))
check(_LP.get("borrowings_noncurrent") == 47_583_268_000.0
      and _LP.get("total_debt") == 47_583_268_000.0,
      "٩د والمفردُ والجمعُ اسمانِ لا اسم — حرفانِ كانا يحجبان الدَّين",
      str(_LP.get("total_debt")))

# ── ١٠ · الحصادُ يجري بتزامنٍ محدودٍ لا ورقةً ورقة (D354) ────────────────
# قِيس على خادم المالك: ستّون ورقةً في 569 ثانيةً — 9.5 ثانيةً للورقة،
# فاللقطةُ كلُّها (272) ثلاثٌ وأربعون دقيقةً من الانتظار على شاشته.
_peak = {"now": 0, "max": 0}
_real_read = xb.read_symbol


async def _slow(sym):
    _peak["now"] += 1
    _peak["max"] = max(_peak["max"], _peak["now"])
    await asyncio.sleep(0.05)
    _peak["now"] -= 1
    return {"annual": [{"as_of": "2025-12-31", "year": 2025, "revenue": 1.0}],
            "quarterly": [], "as_of": _dt.date.today().isoformat()}


xb.read_symbol = _slow                                           # type: ignore[assignment]
import app.services.tadawul_market as _tmk                        # noqa: E402
_keep_rows = _tmk.usable_rows
_tmk.usable_rows = lambda: ({f"S{i}": {"company_url": "/x"}       # type: ignore[assignment]
                             for i in range(12)}, True, "now")
_rep = asyncio.run(xb.refresh([f"S{i}" for i in range(12)], conc=4))
xb.read_symbol = _real_read                                      # type: ignore[assignment]
_tmk.usable_rows = _keep_rows                                    # type: ignore[assignment]
check(_peak["max"] > 1,
      "١٠ الحصادُ متزامنٌ — لا ينتظر كلَّ ملفٍّ قبل طلب التالي",
      f"أعلى تزامنٍ مقيس: {_peak['max']}")
check(_peak["max"] <= 4,
      "١٠ب والسقفُ محدودٌ كما أُعلن — لا عشراتُ وصلاتٍ على المصدر",
      f"{_peak['max']} ≤ 4")
check(_rep.get("قُرئت") == 12 and sum(_rep.values()) == 12,
      "١٠ج والتقريرُ يُحصي كلَّ ورقةٍ مرّةً واحدةً تحت التزامن",
      str(_rep))

print(("FAIL" if fail else "PASS") + " D263 — قوائمُ XBRL الرسمية")
raise SystemExit(fail)
