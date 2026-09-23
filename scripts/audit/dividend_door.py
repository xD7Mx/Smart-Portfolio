#!/usr/bin/env python3
"""أين تنشر «تداول» توزيعاتِ الشركة — خدماتُ صفحة الشركة كما هي (D440). قارئٌ فقط.

    docker exec sp_backend python /app/scripts/audit/dividend_door.py

التوزيعاتُ في صفحة السهم من ياهو وحدَه، فتغيب متى عجز. وقاعدةُ
FETCH_METHOD: تُقرأ أسماءُ الخدمات من الصفحة لا تُخمَّن. فتُطبع كلُّ
الخدمات في صفحة شركتين، ويُنادى ما يوحي بتوزيعٍ أو إجراءٍ مؤسّسيّ.
"""
import asyncio, json, re, sys
sys.path.insert(0, "/app")
_HINT = re.compile(r"ivid|ction|ntitle|istrib|ayout|ividend", re.I)


async def main():
    try:
        from app.services import tadawul_ownership as O
        from app.services.tadawul_http import fetch
    except ModuleNotFoundError as e:
        print(f"⚠ بيئةٌ ناقصة ({e.name}) — لم يُقَس"); return 0
    for sym in ("2222", "4030"):
        body = await O.company_page(sym) or ""
        mb = O._BASE_RE.search(body)
        base = mb.group(1).rstrip("/") if mb else ""
        names = sorted(set(O._EP_RE.findall(body)))
        print(f"═ {sym} · {len(body)} حرفاً · خدمات: {names}")
        for m in re.finditer(r"[Dd]ividend", body):
            print("   ↳ نصّ:", re.sub(r"\s+", " ", body[max(0, m.start()-120):m.end()+160])[:280])
            break
        for n in names:
            if not _HINT.search(n):
                continue
            ep = next(m.group(0) for m in O._EP_RE.finditer(body) if m.group(1) == n)
            st, raw = await fetch(f"{base}/{ep}", params={"requestLocale": "en"}, referer=base)
            print(f"   ✦ {n} — HTTP {st} · {len(raw or '')} · {(raw or '')[:400]!r}")
    return 0

sys.exit(asyncio.run(main()))
