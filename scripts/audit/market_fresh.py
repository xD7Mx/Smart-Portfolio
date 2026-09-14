#!/usr/bin/env python3
"""طزاجةُ قسم السوق وصفقاتُه — قياسٌ من داخل الحاوية (D292).

    docker exec sp_backend python /app/scripts/audit/market_fresh.py
    docker exec sp_backend python /app/scripts/audit/market_fresh.py --apply

قال المالك: «قسمُ السوق غير محدَّث» و«تأكّد من ظهور نتيجةٍ للصفقات
الخاصة — لا أريدها ديكوراً». فهذا يقيس **عمرَ كلّ بطاقةٍ** في القسم،
ويُشغّل جلبَ الصفقات فعلاً ويطبع ما وصل. و`--apply` يحفظ ما قُرئ.
"""
from __future__ import annotations

import asyncio
import datetime as dt
import sys

sys.path.insert(0, "/app")
sys.path.insert(0, "backend")


def line(k: str, v) -> None:
    print(f"  {k:<30} {v}")


def _age(iso) -> str:
    if not iso:
        return "لا زمن"
    try:
        t = dt.datetime.fromisoformat(str(iso))
        if t.tzinfo is None:
            t = t.replace(tzinfo=dt.timezone.utc)
        sec = (dt.datetime.now(dt.timezone.utc) - t).total_seconds()
    except Exception:                                             # noqa: BLE001
        return f"زمنٌ غيرُ مقروء ({iso})"
    if sec < 90:
        return f"{sec:.0f}ث"
    if sec < 5400:
        return f"{sec / 60:.0f}د"
    return f"{sec / 3600:.1f}س"


async def main() -> int:
    apply = "--apply" in sys.argv
    from app.services import cache, lastgood

    print("\n١) طزاجةُ بطاقات قسم السوق")
    from app.services.market_phase import market_phase
    now = dt.datetime.now()
    ph = market_phase((now.weekday() + 1) % 7, now.hour * 60 + now.minute)
    line("طورُ السوق الآن", f"{ph} · {now:%H:%M}")

    from app.services.tadawul_market import age_seconds, usable_rows
    rows, live, at = usable_rows()
    line("لقطةُ «تداول»", f"{len(rows)} رمزاً · {'حيّة' if live else 'آخرُ إغلاق'}"
                          f" · عمرٌ {_age(at)}")
    a = age_seconds()
    line("عمرُ اللقطة بالثواني", f"{a:.0f}ث" if a is not None else "—")

    for key, name in (("market:movers", "الرابحون والخاسرون"),
                      ("market:screener", "فرزُ السوق"),
                      ("market:tasi:tadawul", "مؤشّرُ تاسي"),
                      ("market:special_deals", "الصفقاتُ الخاصة"),
                      ("market:calendar:full", "مفكرةُ السوق")):
        rec = cache.get(key)
        where = "الذاكرة"
        if not isinstance(rec, dict):
            rec = lastgood.load(key)
            where = "المخزن"
        if not isinstance(rec, dict):
            line(name, "غير موجودة")
            continue
        stamp = rec.get("at") or rec.get("as_of") or rec.get("computed_at")
        n = (len(rec.get("deals") or rec.get("rows") or rec.get("items") or [])
             or len(rec))
        line(name, f"{where} · عمرٌ {_age(stamp)} · {n} عنصراً")

    # ── ٢ · الصفقاتُ الخاصة: تُجلَب الآن ويُطبع ما وصل ──────────────────
    print("\n٢) الصفقاتُ الخاصة — جلبٌ حقيقيٌّ الآن")
    from app.services import special_deals as sd
    from app.services.tadawul_http import smart_fetch

    # وتعذُّرُ الشبكة يُقال سطراً — لا يُسقط المسبارَ بأثرٍ طويل.
    try:
        status, body = await smart_fetch(sd.ARGAAM_MARKET,
                                         warm="https://www.argaam.com/ar",
                                         referer="https://www.argaam.com/ar")
    except Exception as e:                                        # noqa: BLE001
        status, body = 0, ""
        line("صفحةُ «أرقام»", f"تعذّر: {type(e).__name__}: {str(e)[:70]}")
    else:
        line("صفحةُ «أرقام»", f"HTTP {status} · {len(body or '')} حرفاً")
    if body:
        import re
        line("جداولُ الصفحة", len(re.findall(r"<table", body, re.I)))
        rows2 = sd.rows_from_html(body)
        line("صفقاتٌ فُهمت", len(rows2))
        for d in rows2[:6]:
            print("     " + str(d))
        if not rows2:
            # ══ صفرُ جداولَ في 494 ألفَ حرف ⇒ الصفوفُ من نداءٍ آخر ══
            # القياسُ الأوّلُ اختلق ثلاثَ «صفقات» من قائمة التنقّل (D293)،
            # فحُرز القارئ. والآن يُبحَث عن **مصدر الصفوف الحقيقيّ**:
            # نداءاتُ الصفحة نفسِها بأنماطها. فيُبنى القارئُ على ما ورد.
            line("صفوفُ <tr>", len(re.findall(r"<tr", body, re.I)))
            print("     نداءاتٌ مرشَّحةٌ في الصفحة:")
            pats = (r'url\s*:\s*[\x27"]([^\x27"]{8,140})',
                    r'data-url="([^"]{8,140})"',
                    r'\$\.(?:get|post|ajax)\(\s*[\x27"]([^\x27"]{8,140})',
                    r'"(/ar/[A-Za-z0-9/_\-]{6,90}(?:json|data|partial|list|deals)[A-Za-z0-9/_\-]*)"',
                    r'(/ar/[A-Za-z]+/[A-Za-z]*[Dd]eal[A-Za-z]*[^"\x27 ]{0,60})')
            seen = []
            for pat in pats:
                for h in re.findall(pat, body):
                    if h not in seen and not h.lower().endswith((".js", ".css",
                                                                 ".png", ".jpg",
                                                                 ".svg", ".woff2")):
                        seen.append(h)
            for h in seen[:16]:
                print("       " + h[:120])
            if not seen:
                print("       — لا نداءَ مطابقاً؛ فالصفوفُ تُرسَم بسكربتٍ مغلَّف")
            # وسياقُ الكلمة الدالّة: أين تقع «الصفقات الخاصة» في الصفحة
            i = body.find("الصفقات الخاصة")
            if i > 0:
                ctx = re.sub(r"\s+", " ", body[i:i + 400])
                print("     سياقُ «الصفقات الخاصة»: " + ctx[:180])
    # ── ٣ · مطاردةُ نقطةِ الصفوف — مصفوفةٌ واحدةٌ تحسم ─────────────────
    # قِيس أن المسارَ نفسَه يظهر في سكربت الصفحة نداءً، وأن الصفحةَ بلا
    # صفوف. فالصفوفُ تُطلب بطلبٍ ثانٍ — وشكلُه يُقاس لا يُخمَّن: طريقةٌ
    # (‏GET/POST) وترويسةُ XHR ومعاملاتٌ بأسماءٍ مرشَّحة (D294).
    print("\n٣) مطاردةُ نقطة الصفوف — تُجرَّب ست صيغ")
    XHR = {"X-Requested-With": "XMLHttpRequest",
           "Accept": "text/html, */*; q=0.01"}
    EP = "https://www.argaam.com/ar/shareholder/shareholders-history-deals"
    tries = [
        ("GET  + XHR", "GET", {"marketid": 3, "pageno": 1}, None, XHR),
        ("POST + XHR (pageno)", "POST", None,
         {"marketid": 3, "pageno": 1}, XHR),
        ("POST + XHR (pageNo)", "POST", None,
         {"marketId": 3, "pageNo": 1}, XHR),
        ("POST + XHR (فارغ)", "POST", None, {}, XHR),
        ("GET  بلا ترويسة", "GET", {"marketid": 3, "pageno": 1}, None, None),
        ("POST + XHR (تواريخ)", "POST", None,
         {"marketid": 3, "pageno": 1, "fromdate": "", "todate": ""}, XHR),
    ]
    best = None
    for label, method, prm, body, hdr in tries:
        try:
            st, txt = await smart_fetch(EP, params=prm, data=body,
                                        method=method, headers=hdr,
                                        warm="https://www.argaam.com/ar",
                                        referer=sd.ARGAAM_MARKET)
        except Exception as e:                                    # noqa: BLE001
            line(label, f"تعذّر: {type(e).__name__}")
            continue
        import re as _r
        trs = len(_r.findall(r"<tr", txt or "", _r.I))
        got = sd.rows_from_html(txt or "")
        line(label, f"HTTP {st} · {len(txt or '')} حرفاً · <tr>={trs} · "
                    f"صفقاتٌ={len(got)}")
        if got and (best is None or len(got) > len(best[1])):
            best = (label, got)
        if trs and not got:
            # صفوفٌ موجودةٌ ولم تُفهَم: يُطبع أوّلُها ليُبنى القارئُ عليها
            row = _r.search(r"<tr[^>]*>(.*?)</tr>", txt, _r.S | _r.I)
            if row:
                clean = _r.sub(r"\s+", " ", _r.sub(r"<[^>]+>", " | ",
                                                   row.group(1))).strip()
                print("       أوّلُ صفّ: " + clean[:150])
    if best:
        print(f"\n   ✔ الصيغةُ العاملة: {best[0]} — {len(best[1])} صفقة")
        for d in best[1][:5]:
            print("     " + str(d))
    if apply:
        print("\n" + str(await sd.refresh()))
    print(f"\nقِيس في {dt.datetime.now():%Y-%m-%d %H:%M}\n")
    return 0


raise SystemExit(asyncio.run(main()))
