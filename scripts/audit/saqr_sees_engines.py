#!/usr/bin/env python3
"""صقرُ يدُ التطبيق: يرى ما يراه المحرّكان باسمائهما في التطبيق (D437).

    python3 scripts/audit/saqr_sees_engines.py

قال المالك: «صقرُ لا يجوز أن يكون مستقلّاً، بل هو امتدادٌ للتطبيق بكامل
بياناته… اجعل صقرَ يدَ التطبيق بلا أخطاءٍ ولا نقصِ ارتباط».

وقِيس: حين يُسأل صقرُ عن شركة، يصله صفُّها من جدول السوق بالسعر وRSI
والعائد ودرجة الجودة — **ولا يصله السعرُ العادل ولا فجوتُه ولا ثقتُه ولا
القرار**، وهي خلاصةُ المحرّكَين اللذين عليهما يقوم التطبيق. فيُسأل عن
السعر العادل فلا رقمَ من المحرّك في يده. ويسمّي الدرجةَ «درجة الحوكمة»
والتطبيقُ يسمّيها «درجة الجودة المالية» — اسمان لرقمٍ واحد.

والفحصُ سلوكيّ: يُنادى بناءُ سياق صقر الحقيقيُّ بسؤالٍ يذكر شركةً وجدولٍ
مُصطنَعٍ يحمل حقولَ المحرّكَين، ويُشترط أن تصل كلُّها **بأسمائها في التطبيق**.
"""
from __future__ import annotations

import os as _os, tempfile as _tf
_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX
_os.environ["SP_STATUS_LOG"] = _os.path.join(_SANDBOX, "status_codes.jsonl")

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")

fail = 0


def check(ok: bool, label: str, detail: str = "") -> None:
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {detail}" if detail else ""))


try:
    from app.services import ai_chat as C
    from app.services import market_screener as MS
except ModuleNotFoundError as e:
    print(f"⚠ بيئةٌ ناقصة ({e.name}) — لم يُقَس")
    sys.exit(0)

ROW = {"symbol": "2010", "name": "سابك", "sector": "المواد الأساسية",
       "price": 60.0, "change_pct": 0.5, "rsi": 48.0,
       "dividend_yield": 4.1, "finance_score": 72.0,
       "fair_value": 71.5, "fair_value_upside_pct": 19.2,
       "fair_value_conf": "متوسطة", "analyst_target": 74.0,
       "decision": "شراء"}
MS.get_cached_screener = lambda: [ROW]

ctx = C._market_context("ما السعر العادل لسابك 2010؟")
rows = ctx.get("بيانات الفرز") or []
r = rows[0] if rows else {}
check(bool(r), "٠ الشركةُ المذكورةُ تصل سياقَ صقر", str(r)[:100])

WANT = {"السعر العادل": 71.5, "الفجوة عن السعر العادل٪": 19.2,
        "ثقة السعر العادل": "متوسطة", "هدف المحللين": 74.0,
        "القرار": "شراء", "درجة الجودة المالية": 72.0}
for k, v in WANT.items():
    check(r.get(k) == v, f"١ «{k}» يصل صقرَ من المحرّك باسمه في التطبيق",
          f"{r.get(k)!r}")
check("درجة الحوكمة" not in r,
      "٢ ولا اسمَ ثانياً للدرجة — «درجة الجودة المالية» كما في التطبيق")

# ── ٣ · وتحليلُ الشركة المحلّيّ في صقر: السعرُ العادلُ واسمُ الدرجة ────
# ‏`ai_analyst.company_analysis` يكتب تحليلَ شركةٍ حين يُسأل صقر عنها.
# وكان يقرأ السعرَ من ياهو (محكوماً بالحصّة) والتطبيقُ يملك لقطةَ «تداول»
# الحيّة، ولا يذكر السعرَ العادل، ويسمّي الدرجةَ «درجة المتانة».
import asyncio                                                       # noqa: E402
try:
    from app.services import ai_analyst as A
    from app.services import analysis as AN
    from app.services import tadawul_market as TM
    from app.services import market_data as MD

    async def _eng(*_a, **_k):
        return {"fair_value": 71.5, "fair_value_upside_pct": 19.2,
                "fair_value_conf": "متوسطة", "price": 60.0,
                "governance": {"score": 72, "evaluable": True}}
    AN.analyze_company = _eng
    TM.row_for = lambda sym: {"price": 60.0}
    _yahoo = {"n": 0}

    async def _gp(*_a, **_k):
        _yahoo["n"] += 1
        return None
    MD.market_service.get_price = _gp
    txt = asyncio.run(A.company_analysis(None, {"symbol": "2010", "name": "سابك"}, {}))
    check("السعر العادل" in txt and "71.5" in txt,
          "٣ تحليلُ صقر للشركة يذكر السعرَ العادل من المحرّك", txt[:160].replace("\n", " "))
    check("درجة الجودة المالية" in txt and "درجة المتانة" not in txt,
          "٣ب واسمُ الدرجة كما في التطبيق — لا «درجة المتانة»")
    check(_yahoo["n"] == 0,
          "٣ج والسعرُ من لقطة «تداول» الرسمية — لا نداءَ لياهو", f"نداءاتُ ياهو: {_yahoo['n']}")
except ModuleNotFoundError as e:
    print(f"⚠ ٣ لم يُقَس ({e.name})")

print(("FAIL" if fail else "PASS")
      + " D437 — صقرُ يرى خلاصةَ المحرّكَين بأسمائها في التطبيق")
sys.exit(fail)
