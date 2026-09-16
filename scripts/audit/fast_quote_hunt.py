#!/usr/bin/env python3
"""هل في «تداول» بابٌ أسرعُ من أربعِ دقائق؟ — قياسٌ قبل أيّ وعد (D327).

    docker exec sp_backend python /app/scripts/audit/fast_quote_hunt.py 24 5

قِيس (D326) أنّ جدولَ مراقبة السوق ينشر كلَّ ‎٤:٢٣–‎٤:٢٦ ويقول
`max-age=300`. وفي الصفحة نفسِها بابان «حيّان» تناديهما ترويستُها
باستمرار — قِيسا في D311 فبانا: `RefreshTradeDetailsServlet` تحديثُ
ترويسة المؤشّر (`tasiValue` · `mt30`)، و`TickerServlet` لقطةُ السوق.
فهل إيقاعُهما أسرع؟

ولا يُوعَد بشيءٍ قبل أن يُقاس. فلكلّ بابٍ يُطبع في كلّ نداء: **بصمةُ
الجسم** ورقمٌ منه (قيمةُ تاسي أو أوّلُ سعر) ورؤوسُ الذاكرة، ثمّ في
الخاتمة: **كم مرّةً تغيّر الرقمُ وبكم ثانيةٍ بين تغيّرين** — وذلك هو
السقفُ الحقيقيُّ لأيّ «فورية» تُبنى عليه.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import re
import sys
import time

sys.path.insert(0, "/app")
sys.path.insert(0, "backend")

ROUNDS = int(sys.argv[1]) if len(sys.argv) > 1 else 24
GAP = float(sys.argv[2]) if len(sys.argv) > 2 else 5.0

BASE = "https://www.saudiexchange.sa/tadawul.eportal.theme.helper/"
DOORS = {
    "RefreshTradeDetails": BASE + "RefreshTradeDetailsServlet",
    "Ticker": BASE + "TickerServlet",
    # والبابُ الذي كان قارئُ المؤشّر يناديه — يُقاس هو أيضاً لا يُستثنى
    # (كان موروثاً بلا قياس · D327).
    "ThemeTASIUtility": BASE + "ThemeTASIUtilityServlet",
}
# رقمٌ واحدٌ يُقرأ من الجسم بمعناه — لا بموضعٍ ثابت.
_NUM = re.compile(r'"?(tasiValue|lastPrice|price|value)"?\s*[:=]\s*"?'
                  r'([0-9][0-9,]*\.?[0-9]*)', re.I)


def _pluck(body: str) -> str:
    m = _NUM.search(body or "")
    if m:
        return f"{m.group(1)}={m.group(2)}"
    nums = re.findall(r"[0-9][0-9,]{2,}\.[0-9]+", body or "")
    return f"أوّلُ رقم={nums[0]}" if nums else "—"


async def _headers(url: str, referer: str) -> str:
    try:
        from curl_cffi import requests as _cr
        r = await asyncio.to_thread(
            lambda: _cr.get(url, headers={"Referer": referer,
                                          "X-Requested-With": "XMLHttpRequest"},
                            impersonate="chrome", timeout=30))
        h = {k.lower(): v for k, v in dict(r.headers).items()}
        keep = [f"{k}: {h[k]}" for k in
                ("cache-control", "age", "x-cache", "expires", "pragma")
                if k in h]
        return " · ".join(keep) or "(لا رؤوسَ ذاكرة)"
    except Exception as e:                                        # noqa: BLE001
        return f"تعذّر: {type(e).__name__}: {e}"


async def main() -> int:
    from datetime import datetime, timedelta, timezone

    from app.services.market_phase import market_phase
    from app.services.special_deals import TD_HOME
    from app.services.tadawul_http import fetch

    now = datetime.now(timezone(timedelta(hours=3)))
    phase = market_phase((now.weekday() + 1) % 7, now.hour * 60 + now.minute)
    print(f"═ ساعةُ الرياض {now:%H:%M:%S} · الطورُ «{phase}» ═")
    if phase == "closed":
        print("  (مغلقٌ — فثباتُ الرقم ليس حكماً على الباب.)")

    # تُسخَّن الجلسةُ بالصفحة كما تفعل الترويسةُ نفسُها.
    try:
        st, _ = await fetch(TD_HOME)
        print(f"  تسخينُ الجلسة: HTTP {st}")
    except Exception as e:                                        # noqa: BLE001
        print(f"  تسخينُ الجلسة تعذّر: {type(e).__name__}")

    print("\n═ رؤوسُ كلّ باب ═")
    for name, url in DOORS.items():
        print(f"  {name}: {await _headers(url, TD_HOME)}")

    hist: dict[str, list[tuple[float, str, str]]] = {k: [] for k in DOORS}
    print(f"\n═ رصدٌ: {ROUNDS} نداءً بفاصل {GAP:.0f}ث "
          f"(~{ROUNDS * GAP / 60:.1f} دقيقة) ═")
    t_start = time.monotonic()
    for i in range(ROUNDS):
        line = [f"[{i+1:2d}] {time.monotonic() - t_start:5.0f}ث"]
        for name, url in DOORS.items():
            try:
                st, body = await fetch(url, referer=TD_HOME, timeout=25)
            except Exception as e:                                # noqa: BLE001
                line.append(f"{name}: تعذّر {type(e).__name__}")
                continue
            if st != 200 or not body:
                line.append(f"{name}: HTTP {st}")
                continue
            dig = hashlib.sha256(body.encode()).hexdigest()[:8]
            val = _pluck(body)
            hist[name].append((time.monotonic() - t_start, dig, val))
            line.append(f"{name}: {dig} · {val}")
        print("   " + " | ".join(line))
        if i + 1 < ROUNDS:
            await asyncio.sleep(GAP)

    print("\n═ الحكم — لكلّ بابٍ إيقاعُه المقيس ═")
    best = None
    for name, seq in hist.items():
        if len(seq) < 2:
            print(f"  {name}: لم تُقرأ قراءتان — لا حكم.")
            continue
        marks = [seq[i][0] for i in range(1, len(seq))
                 if seq[i][2] != seq[i - 1][2]]
        span = seq[-1][0] - seq[0][0]
        if not marks:
            print(f"  {name}: الرقمُ لم يتغيّر في {span:.0f} ثانية — "
                  "فليس أسرعَ من جدول مراقبة السوق (أو الرصدُ أقصرُ من"
                  " إيقاعه).")
            continue
        gaps = [marks[0]] + [marks[i] - marks[i - 1]
                             for i in range(1, len(marks))]
        med = sorted(gaps)[len(gaps) // 2]
        print(f"  {name}: تغيّر {len(marks)} مرّةً في {span:.0f} ثانية · "
              f"وسيطُ الفاصل {med:.0f}ث · الفواصل "
              + " · ".join(f"{g:.0f}" for g in gaps[:8]))
        if best is None or med < best[1]:
            best = (name, med)

    print()
    if best and best[1] <= 60:
        print(f"الخلاصة: **«{best[0]}» ينشر كلَّ ~{best[1]:.0f} ثانية** — "
              "أسرعُ من أربع دقائق، فيُبنى عليه رقمُ الشاشة الحيُّ "
              "(المؤشّرُ أو السعر) بعد قراءةِ حقوله بالحرف.")
        return 0
    if best:
        print(f"الخلاصة: أسرعُ بابٍ قِيس «{best[0]}» بوسيطِ "
              f"{best[1]:.0f}ث — لا مكسبَ يُذكر على جدول المراقبة. "
              "ولا يُوعَد بفوريةٍ من مصدرٍ عامّ.")
        return 1
    print("الخلاصة: لم يتغيّر رقمٌ في أيّ بابٍ خلال الرصد — يُعاد الرصدُ "
          "أطولَ في جلسةٍ مفتوحة، أو يُقال إنّ المصدرَ العامّ لا يقدّم "
          "أسرعَ من أربع دقائق.")
    return 1


raise SystemExit(asyncio.run(main()))
