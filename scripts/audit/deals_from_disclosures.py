#!/usr/bin/env python3
"""هل تُفصَح الصفقاتُ الخاصة في إفصاحات «تداول»؟ — قياسٌ واحد.

    docker exec sp_backend python /app/scripts/audit/deals_from_disclosures.py

قِيس أن الصفقاتَ الخاصة لم تبقَ في مصدرٍ عامّ: مسارُ «تداول» يُصرَف إلى
صفحةٍ أخرى، وقائمتُها ٤١٦ رابطاً بصفرِ ذكرٍ للصفقات، و«أرقام» تبيعها في
باقةٍ بـ٧٥٠٠ ريال. وبقي بابٌ رسميٌّ مبنيٌّ عندنا: **الإفصاحات**.

ويُطبع هنا **الحالُ أوّلاً ثمّ الحكم**: أيُّ مصدرٍ نادى وبأيّ حالةٍ وكم
فُهم منه، ثمّ مفردات العناوين الواصلة، ثمّ ما يذكر صفقةً بأيّ لفظ. فإن
عاد صفرٌ عُرف **أصفرُ المصدرِ أم صفرُ قارئِنا** — وهو الفرقُ الذي كلّفنا
دوراتٍ قبلاً.
"""
from __future__ import annotations

import asyncio
import json
import re
import sys
from collections import Counter

sys.path.insert(0, "/app")
sys.path.insert(0, "backend")

# ألفاظُ الصفقة كما قد تُكتب في إفصاحٍ رسميّ — واسعةٌ عن قصد.
STRICT = re.compile(r"صفقة\s*خاصة|صفقات\s*خاصة|صفقة\s*متفاوض|Special\s*Deal",
                    re.I)
ANY_DEAL = re.compile(r"صفق|deal", re.I)


async def main() -> int:
    from app.services.tadawul_announcements import (
        fetch_tadawul_announcements, probe_tadawul,
    )

    # ── ١ · حالُ المصادر: نداءٌ وحالةٌ وحجمٌ وكم فُهم ────────────────────
    print("═ حالُ مصادر الإفصاح ═")
    try:
        rep = await probe_tadawul()
        for label, e in (rep.get("urls") or {}).items():
            if "error" in e:
                print(f"  · {label}: تعذّر — {e['error'][:90]}")
                continue
            print(f"  · {label}: HTTP {e.get('status')} · "
                  f"{e.get('length', 0)} حرفاً · شكلُه {e.get('shape')} · "
                  f"فُهم منه {e.get('parsed_count', 0)}")
            print(f"     {e.get('url', '')[:110]}")
            head = re.sub(r"\s+", " ", str(e.get("content_head") or ""))[:240]
            if head:
                print(f"     أوّلُ الجسم: {head}")
    except Exception as e:                                        # noqa: BLE001
        print(f"  تعذّر فحصُ المصادر: {type(e).__name__}: {e}")

    # ── ١ب · القشرةُ تُسمّي خدمتَها — فتُنادى وتُقاس ──────────────────
    # قِيس: الصفحةُ صارت ٢٠٠ بـ٥٧٢ ألفَ حرفٍ و«فُهم منها 0» — فهي قشرةٌ
    # يُملأ جدولُها بنداءِ خدمةٍ (كمراقبة السوق · D251). فتُقرأ أسماءُ
    # خدماتها، ويُنادى كلُّ ما يشبه معناها، ويُطبع ما عاد — لا يُخمَّن.
    print("\n═ خدماتُ صفحة الإفصاحات ═")
    from app.services.tadawul_announcements import DEFAULT_TADAWUL_URL
    from app.services.tadawul_http import fetch

    try:
        status, page = await fetch(DEFAULT_TADAWUL_URL)
    except Exception as e:                                        # noqa: BLE001
        print(f"  تعذّر: {type(e).__name__}: {e}")
        page, status = "", 0
    print(f"  الصفحة: HTTP {status} · {len(page or '')} حرفاً · "
          f"{len(re.findall(r'<table', page or '', re.I))} جدولاً · "
          f"{len(re.findall(r'<tr', page or '', re.I))} صفّاً")
    mb = re.search(r"<base[^>]+href=[\"']([^\"']+)", page or "", re.I)
    base = mb.group(1).rstrip("/") if mb else None
    print(f"  أساسُ الصفحة: {base or 'لا شيء'}")
    eps = {}
    for m in re.finditer(r"p0/[A-Za-z0-9_=]*=NJ([A-Za-z][A-Za-z0-9_]{3,60})=/",
                         page or ""):
        eps.setdefault(m.group(1), m.group(0))
    print(f"  أسماءُ خدماتها: {len(eps)}")
    for n in list(eps)[:14]:
        print(f"      {n}")

    served: list[str] = []          # خدماتٌ عادت بصفوفٍ فعلاً
    WANT = re.compile(r"news|announc|disclos|issuer|market|list|data|report",
                      re.I)
    tried = [n for n in eps if WANT.search(n)][:6]
    if base and tried:
        print(f"\n  ── تُنادى {len(tried)} خدمةً بمعناها ──")
    for n in tried:
        url = f"{base}/{eps[n]}"
        for loc in ("ar", "en"):
            try:
                st, body = await fetch(url, params={"requestLocale": loc},
                                       referer=DEFAULT_TADAWUL_URL)
            except Exception as e:                                # noqa: BLE001
                print(f"      {n} [{loc}]: تعذّر {type(e).__name__}")
                continue
            rows = None
            try:
                data = json.loads(body)
                rows = (data.get("data") if isinstance(data, dict) else data)
                rows = len(rows) if isinstance(rows, list) else "—"
            except Exception:                                     # noqa: BLE001
                rows = f"{len(re.findall(r'<tr', body or '', re.I))} صفّاً"
            head = re.sub(r"\s+", " ", (body or "")[:180])
            print(f"      {n} [{loc}]: HTTP {st} · {len(body or '')} حرفاً · "
                  f"صفوف={rows}")
            if body:
                print(f"         {head}")
            if st == 200 and body:
                if (isinstance(rows, int) and rows > 0) or (
                        isinstance(rows, str) and not rows.startswith("0 ")):
                    served.append(f"{n}[{loc}]:{rows}")
                break

    # ── ٢ · ما وصل فعلاً ───────────────────────────────────────────────
    try:
        items = await fetch_tadawul_announcements(force=True)
    except Exception as e:                                        # noqa: BLE001
        print(f"\nتعذّر جلبُ الإفصاحات: {type(e).__name__}: {e}")
        return 1
    print(f"\n═ إفصاحاتٌ وصلت: {len(items)} ═")
    dates = sorted(str(i.get("date") or "") for i in items if i.get("date"))
    if dates:
        print(f"  مداها: {dates[0]} … {dates[-1]}")
    if items:
        kinds = Counter(str(i.get("type") or "—") for i in items)
        print("  تصنيفاتُها: "
              + " · ".join(f"{k}:{n}" for k, n in kinds.most_common(8)))
        print("  عيّنةُ عناوين:")
        for i in items[:6]:
            print(f"     {i.get('date','')} · {i.get('symbol') or '—'} · "
                  f"{str(i.get('title',''))[:95]}")

    # ── ٣ · وما يذكر صفقةً — بأيّ لفظ، ثمّ باللفظ الدقيق ───────────────
    wide = [i for i in items if ANY_DEAL.search(str(i.get("title", "")))]
    print(f"\n═ عناوينُ تذكر «صفق/deal» بأيّ صيغة: {len(wide)} ═")
    for i in wide[:20]:
        print(f"   {i.get('date','')} · {i.get('symbol') or '—'} · "
              f"{str(i.get('title',''))[:110]}")

    hits = [i for i in items if STRICT.search(str(i.get("title", "")))]
    print(f"\n═ وباللفظ الدقيق «صفقة خاصة»: {len(hits)} ═")
    for i in hits[:20]:
        print("   " + json.dumps(
            {k: i.get(k) for k in ("date", "symbol", "title", "url")},
            ensure_ascii=False)[:220])

    # ── ٤ · الحكمُ يُقال، ولا يُترك للقارئ ─────────────────────────────
    print()
    if not items and served:
        print("الحكم: القارئُ لا يفهم القشرة، **وخدمتُها أعطت صفوفاً**: "
              + " · ".join(served)
              + " — فيُبنى القارئُ على هذه الخدمة بعينها.")
    elif not items:
        print("الحكم: لم يصل إفصاحٌ واحد ولا خدمةٌ أعطت صفوفاً — فالعطبُ في"
              " المصدر أو في نداءِنا، لا في البحث. (انظر أعلاه.)")
    elif not wide:
        print("الحكم: الإفصاحاتُ تصل، ولا يُذكر فيها لفظُ صفقةٍ أصلاً —"
              " فالصفقاتُ الخاصة لا تُنشَر في هذه القناة.")
    elif not hits:
        print("الحكم: تُذكر صفقاتٌ بألفاظٍ أخرى (أعلاه) ولا يُذكر «صفقة"
              " خاصة» — تُقرأ المفرداتُ الواصلةُ ويُبنى المطابقُ عليها.")
    else:
        print(f"الحكم: نعم — {len(hits)} إفصاحاً يذكر صفقةً خاصة."
              " يُبنى القارئُ على هذه القناة الرسمية.")
    return 0


raise SystemExit(asyncio.run(main()))
