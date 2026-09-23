#!/usr/bin/env python3
"""جدولُ توزيعات الشركة في صفحتها الرسمية بـ«تداول» — صفوفُه كما هي (D444). قارئٌ فقط.

    docker exec sp_backend python /app/scripts/audit/company_dividends_table.py
"""
import asyncio, re, sys, html as H
sys.path.insert(0, "/app")


async def main():
    try:
        from app.services import tadawul_ownership as O
        from app.services.tadawul_http import fetch
    except ModuleNotFoundError as e:
        print(f"⚠ بيئةٌ ناقصة ({e.name}) — لم يُقَس"); return 0
    for sym in ("4030", "2222", "1120"):
        body = await O.company_page(sym) or ""
        i = body.find('id="companyDividends"')
        seg = body[i:body.find("</table>", i)] if i >= 0 else ""
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", seg, re.S)
        cells = [[H.unescape(re.sub(r"<[^>]+>|\s+", " ", c)).strip() for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", r, re.S)] for r in rows]
        print(f"═ {sym} · جدولٌ={'نعم' if i >= 0 else 'لا'} · صفوف={len(cells)}")
        for c in cells[:8]:
            print("   ", c)
        mb = O._BASE_RE.search(body)
        base = mb.group(1).rstrip("/") if mb else ""
        ep = next((m.group(0) for m in O._EP_RE.finditer(body) if m.group(1) == "getCorporateAction"), None)
        if ep:
            for it in ("", "ALL", "1"):
                st, raw = await fetch(f"{base}/{ep}", params={"indexSymbol": sym, "language": "en", "issueType": it}, referer=base)
                print(f"   ✦ getCorporateAction issueType={it!r} — {st} · {(raw or '')[:300]!r}")
    return 0

sys.exit(asyncio.run(main()))
