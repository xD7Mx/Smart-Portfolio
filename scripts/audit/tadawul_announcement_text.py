#!/usr/bin/env python3
"""نصُّ الإفصاح من «تداول» أوّلاً (D467) — قياسٌ قبل البناء. قارئٌ فقط.

    docker exec sp_backend python /app/scripts/audit/tadawul_announcement_text.py
"""
import asyncio, json, re, sys
sys.path.insert(0, "/app")
_SVC = re.compile(r"p0/[A-Za-z0-9_=]*=NJ([A-Za-z][A-Za-z0-9_]{3,60})=/")
O = "https://www.saudiexchange.sa"
PAGE = O + "/wps/portal/saudiexchange/newsandreports/issuer-news/issuer-announcements?locale=ar"


def blocks(h):
    """أكبرُ الكتل النصّية في الصفحة (بلا سكربت/نمط) — لإيجاد المتن."""
    h = re.sub(r"<script.*?</script>|<style.*?</style>", "", h or "", flags=re.S)
    out = []
    for m in re.finditer(r"<(div|td|p|section|article)[^>]*>(.*?)</\1>", h, re.S):
        t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(2))).strip()
        if len(t) > 80 and not re.search(r"تسجيل الدخول|السوق مغلق|Log in", t):
            out.append((len(t), m.group(0)[:160], t))
    return sorted(out, reverse=True)[:4]


async def main():
    try:
        from app.services.tadawul_http import fetch, smart_fetch
    except ModuleNotFoundError as e:
        print(f"⚠ بيئةٌ ناقصة ({e.name}) — لم يُقَس"); return 0
    st, page = await fetch(PAGE)
    base = (re.search(r"<base[^>]+href=[\"']([^\"']+)", page or "") or [None, ""])[1].rstrip("/")
    ep = next((m.group(0) for m in _SVC.finditer(page or "") if m.group(1) == "getAnnouncementListData"), None)
    print(f"الصفحة: HTTP {st} · الخدمة: {bool(ep)}")
    form = {"annoucmentType": "1_-1", "symbol": "4001", "sectorDpId": "", "searchType": "", "fromDate": "", "toDate": "",
            "datePeriod": "", "productType": "", "advisorsList": "", "textSearch": "", "pageNumberDb": "1", "pageSize": "10"}
    st2, raw = await smart_fetch(f"{base}/{ep}", method="POST", data=form, referer=PAGE,
                                 warm=PAGE, headers={"X-Requested-With": "XMLHttpRequest"})
    try:
        j = json.loads(raw)
    except Exception:
        print(f"POST: HTTP {st2} · {(raw or '')[:300]!r}"); return 0
    L = j.get("announcementList") or []
    print(f"POST رمز 4001: HTTP {st2} · {len(L)} · المجموع {L[0].get('totalCount') if L else 0} · رموز: {sorted(set(x.get('SYMBOL') for x in L))}")
    for x in L[:6]:
        print(f"  {x.get('PR_DATE')} · {x.get('SYMBOL')} · {(x.get('SHORT_DESC') or '')[:90]} · {x.get('announcementUrl','')[-60:]}")
    print("  مفاتيحُ الصفّ:", sorted(L[0].keys()) if L else [])
    for x in L[:2]:
        du = O + x["announcementUrl"].replace("locale=en", "locale=ar")
        st3, h3 = await fetch(du)
        print(f"\nتفاصيل {x.get('announcementNumber')}: HTTP {st3} · {len(h3 or '')}")
        for n, tag, t in blocks(h3):
            print(f"  كتلة {n} حرف · {tag!r}\n    {t[:700]}")
        for m in re.finditer(r'(?:href|src)="([^"]*\.pdf[^"]*)"', h3 or "", re.I):
            print(f"  PDF: {m.group(1)[:160]}"); break
        break
    du = O + L[0]["announcementUrl"].replace("locale=en", "locale=ar")
    st4, h4 = await fetch(du)
    h4 = h4 or ""
    idx = [m.start() for m in re.finditer("استقالة", h4)]
    print(f"\nالثابت: {len(h4)} · مواضعُ «استقالة»: {idx[:12]}")
    for k in idx[:8]:
        print(f"  @{k}: {h4[max(0,k-400):k+500]!r}\n")
    return 0

sys.exit(asyncio.run(main()))
