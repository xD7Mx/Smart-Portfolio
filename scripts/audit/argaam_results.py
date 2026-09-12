#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# D253 — الربعيُّ من مصدرٍ يُرسَم في الخادم، والرمزُ يُقرأ ولا يُخمَّن.
#
# طلب المالك ربعياً («كانت على ياهو فاضية»). وقياسُ المصادر أعطى خريطةً:
# تبويبُ قوائم «تداول» متجمّدٌ عند ‎2023، وصفحاتُ «أرقام» للقوائم والنِسَب
# وصفقاتُ «تداول» الخاصّة تُرسَم بجافاسكربت — ومسارٌ واحدٌ يُرسَم في
# الخادم: نتائجُ الشركات في «أرقام» (‏274 صفّاً، ربعياً وسنوياً).
#
# وخطرُه في المطابقة: الجدولُ يسمّي الشركةَ باسمها المختصر لا برمزها،
# ومطابقةُ الأسماء تقريباً تُدخل أرباحَ شركةٍ في ملفّ أخرى — أسوأُ من لا
# بيانات. فيُقاس السلوك:
#   ٠· الرمزُ يُؤخذ من معرِّف الرابط عبر خريطةٍ مقيسة
#   ١· ومعرِّفٌ مجهولٌ يُترك ويُعَدّ — لا يُطابَق باسم
#   ٢· وصفٌّ بلا رابطٍ يُترك ويُعَدّ
#   ٣· والسالبُ بين قوسين يُقرأ سالباً
#   ٤· والنسبةُ تُقرأ بإشارتها، و«-» ليست صفراً
#   ٥· وأسماءُ الفترتين تُقرأ من الترويسة لا تُختلق
#   ٦· وجدولٌ قصيرٌ يُرفَض ولا يُحفَظ
#   ٧· وما لم يُجلَب لا يُكتب فوق المحفوظ
# ─────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import os as _os
import tempfile as _tf

_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX

import asyncio  # noqa: E402
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


from app.services import argaam_results as ar  # noqa: E402

IDS = {"2001": "81", "1810": "600", "4141": "104"}

HEAD = ("<tr><th>تاريخ</th><th>الشركة</th><th>الربع الثاني 2025</th>"
        "<th>الربع الثاني 2026</th><th>التغير (%)</th></tr>")


def row(cid, name, prev, cur, chg):
    link = (f"<a href=\"/ar/company/companyoverview/marketid/3/companyid/{cid}\">"
            f"{name}</a>") if cid else name
    return (f"<tr><td>09-08-2026</td><td>{link}</td><td>{prev}</td>"
            f"<td>{cur}</td><td>{chg}</td></tr>")


BODY = "<table>" + HEAD + row("81", "كيمانول", "(337.03)", "(35.25)", "89.54 %") \
    + row("600", "الدريس", "120.00", "150.00", "25.00 %") \
    + row("999", "شركةٌ مجهولة", "10", "12", "20 %") \
    + row(None, "بلا رابط", "10", "12", "20 %") \
    + row("104", "الشرق", "-", "-", "-") + "</table>"

rows, rep = ar.parse(BODY, IDS)

check(set(rows) == {"2001", "1810"},
      "٠ الرمزُ من معرِّف الرابط عبر الخريطة المقيسة", str(sorted(rows)))
check(rep.get("معرِّفٌ مجهول") == 1 and "شركةٌ مجهولة" not in str(rows),
      "١ معرِّفٌ مجهولٌ يُترك ويُعَدّ — لا مطابقةَ باسم", str(rep))
check(rep.get("بلا معرِّف") == 1,
      "٢ وصفٌّ بلا رابطٍ يُترك ويُعَدّ", str(rep.get("بلا معرِّف")))
check(rows["2001"]["prev"] == -337.03 and rows["2001"]["current"] == -35.25,
      "٣ السالبُ بين قوسين يُقرأ سالباً", str(rows["2001"]["prev"]))
check(rows["2001"]["change_pct"] == 89.54 and rows["1810"]["change_pct"] == 25.0,
      "٤ والنسبةُ تُقرأ رقماً بلا علامة", str(rows["1810"]["change_pct"]))
check(rep.get("بلا رقمين") == 1,
      "٤ب و«-» ليست صفراً — صفٌّ بلا رقمين يُترك", str(rep))
check(rows["2001"]["prev_label"] == "الربع الثاني 2025"
      and rows["2001"]["current_label"] == "الربع الثاني 2026",
      "٥ وأسماءُ الفترتين من الترويسة لا مختلَقةً",
      f"{rows['2001']['prev_label']} ← {rows['2001']['current_label']}")

# ── ٦ · ٧ · الرفضُ والحفظ ───────────────────────────────────────────────
async def _fake(fp, year):
    return (BODY if fp == ar.QUARTER else ""), (None if fp == ar.QUARTER else "HTTP 500")


ar.fetch = _fake                                                 # type: ignore[assignment]


async def _ids():
    return {f"{1000 + i}": str(9000 + i) for i in range(250)}


import app.services.argaam_ids as _ai  # noqa: E402
_ai.build = _ids                                                 # type: ignore[assignment]

rec = asyncio.run(ar.refresh(2026))
check("error" in rec and not ar.results("quarter"),
      "٦ جدولٌ لا يُفهم منه إلا القليل يُرفَض ولا يُحفَظ", str(rec)[:110])


async def _ids2():
    return {**{f"{1000 + i}": str(9000 + i) for i in range(250)}, **IDS}


_ai.build = _ids2                                                # type: ignore[assignment]
BIG = "<table>" + HEAD + "".join(
    row(str(9000 + i), f"ش{i}", "10", "12", "20 %") for i in range(120)) + "</table>"


async def _fake2(fp, year):
    return (BIG if fp == ar.QUARTER else ""), (None if fp == ar.QUARTER else "HTTP 500")


ar.fetch = _fake2                                                # type: ignore[assignment]
rec = asyncio.run(ar.refresh(2026))
check(rec.get("ok") and len(ar.results("quarter")) == 120,
      "٦ب وجدولٌ كاملٌ يُحفَظ ويُقرأ", str(rec.get("تفصيل", {}).get("quarter", {}).get("count")))
check(ar.results("annual") == {},
      "٧ والسنويُّ الذي تعذّر جلبُه لا يُكتب فارغاً فوق شيء",
      str(rec.get("تفصيل", {}).get("annual", {}).get("error"))[:40])
# (صُحّح: كان الفحصُ يختار رمزاً موجوداً في الخريطة المموَّهة نفسِها
#  فيتناقض — الغائبُ يُختار من خارجها.)
check(ar.for_symbol("9999.SR") == {} and "quarter" in ar.for_symbol("1010.SR"),
      "٧ب والقراءةُ برمزٍ تعمل بلاحقةٍ وبدونها، والغائبُ يعود فارغاً")

print(("FAIL" if fail else "PASS") + " D253 — نتائجُ الأرباع من مصدرٍ مقروء")
raise SystemExit(fail)
