"""نصُّ الإفصاح من «تداول» أوّلاً و«أرقام» مكمِّلاً (D467).

بأمر المالك: «تداول أوّلاً وأرقام مكمِّلاً». إفصاحاتُ الشركات مصدرُها
الأصليُّ إعلاناتُ «تداول» الرسمية — مجانيةٌ ومنشورةٌ كاملة، و«أرقام» تُعيد
نشرَها. وقِيس (`tadawul_announcement_text.py`):

  · صفحةُ «إعلانات المصدرين» تنادي خدمةً اسمُها `getAnnouncementListData`
    ‏(POST بنموذجٍ حقولُه: annoucmentType · symbol · pageNumberDb · pageSize …)
    فتعود إفصاحاتُ الشركة بتواريخها ورابطِ تفاصيل كلٍّ منها (4001: 300 إفصاح).
  · صفحةُ التفاصيل تحمل المتنَ في HTML نفسِه داخل `announcementBox`:
    العنوانُ في `<h3>` ثمّ جداولُ «بند | توضيح».

والمطابقةُ بين إعلانٍ ظهر في التطبيق وإفصاح «تداول»: الرمزُ نفسُه، والتاريخُ
في ثلاثة أيام، والعنوانُ متقاربٌ بكلماته — فتقريرُ «أرقام» التحليليُّ
المنشورُ يومَ إفصاحٍ آخر لا يُلبَس نصَّ ذلك الإفصاح.
"""
from __future__ import annotations
import datetime as dt
import html as _html
import re

from loguru import logger

from app.services import cache

O = "https://www.saudiexchange.sa"
PAGE = O + "/wps/portal/saudiexchange/newsandreports/issuer-news/issuer-announcements?locale=ar"
_SVC = re.compile(r"p0/[A-Za-z0-9_=]*=NJ([A-Za-z][A-Za-z0-9_]{3,60})=/")
_BASE = re.compile(r"<base[^>]+href=[\"']([^\"']+)", re.I)


async def _endpoint() -> str | None:
    hit = cache.get("tadawul:annlist:ep")
    if hit:
        return hit
    from app.services.tadawul_http import fetch
    st, page = await fetch(PAGE)
    if st != 200 or not page:
        return None
    mb = _BASE.search(page)
    ep = next((m.group(0) for m in _SVC.finditer(page) if m.group(1) == "getAnnouncementListData"), None)
    if not (mb and ep):
        return None
    url = f"{mb.group(1).rstrip('/')}/{ep}"
    cache.set("tadawul:annlist:ep", url, 6 * 60 * 60)
    return url


def _date(s: str) -> str | None:
    for fmt in ("%b %d, %Y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime((s or "").strip(), fmt).date().isoformat()
        except ValueError:
            continue
    return None


async def list_for(symbol: str, size: int = 40) -> list[dict]:
    """إفصاحاتُ الشركة في «تداول»: [{date, url, id}] — الأحدثُ أوّلاً."""
    sym = re.sub(r"\D", "", str(symbol or ""))[:4]
    if len(sym) != 4:
        return []
    ck = f"tadawul:annlist:{sym}"
    hit = cache.get(ck)
    if hit is not None:
        return hit
    ep = await _endpoint()
    if not ep:
        return []
    from app.services.tadawul_http import smart_fetch
    form = {"annoucmentType": "1_-1", "symbol": sym, "sectorDpId": "", "searchType": "", "fromDate": "",
            "toDate": "", "datePeriod": "", "productType": "", "advisorsList": "", "textSearch": "",
            "pageNumberDb": "1", "pageSize": str(size)}
    try:
        import json
        st, raw = await smart_fetch(ep, method="POST", data=form, referer=PAGE, warm=PAGE,
                                    headers={"X-Requested-With": "XMLHttpRequest"})
        rows = (json.loads(raw) or {}).get("announcementList") or [] if st == 200 else []
    except Exception as e:                                         # noqa: BLE001
        logger.debug("إفصاحاتُ تداول لـ{}: {}", sym, e)
        rows = []
    out = []
    for r in rows:
        if str(r.get("SYMBOL")) != sym or not r.get("announcementUrl"):
            continue
        out.append({"date": _date(r.get("PR_DATE")), "id": str(r.get("announcementNumber") or r.get("PRESS_REL_ID")),
                    "url": O + r["announcementUrl"].replace("locale=en", "locale=ar")})
    cache.set(ck, out, 60 * 60 if out else 10 * 60)
    return out


def parse_detail(h: str) -> dict | None:
    """صفحةُ التفاصيل ← {title, text}. المتنُ ما في `announcementBox` وحده."""
    i = (h or "").find('class="announcementBox')
    if i < 0:
        return None
    seg = h[i:i + 120000]
    stop = re.search(r"<script|announcementBoxRt|class=\"attachment", seg[200:])
    if stop:
        seg = seg[:200 + stop.start()]
    mt = re.search(r"<h3[^>]*>(.*?)</h3>", seg, re.S)
    title = re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", "", mt.group(1)))).strip() if mt else ""
    body = seg[mt.end():] if mt else seg
    body = re.sub(r"<a[^>]*id=\"companyProfLink\".*?</a>", "", body, flags=re.S)
    body = re.sub(r"<thead>.*?</thead>", "", body, flags=re.S)             # «بند | توضيح» ترويسةٌ لكلّ جدول
    from app.services.article_body import html_to_text
    text = html_to_text(body)
    text = "\n".join(ln for ln in text.split("\n") if not re.fullmatch(r"[\s|]*", ln) or ln == "")
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(text) < 30:
        return None
    return {"title": title, "text": text}


async def detail(url: str) -> dict | None:
    if not url.startswith(O + "/wps/portal/saudiexchange/newsandreports/issuer-news/issuer-announcements/"):
        return None
    ck = f"tadawul:anndetail:{url}"
    hit = cache.get(ck)
    if hit is not None:
        return hit or None
    from app.services.tadawul_http import fetch
    try:
        st, h = await fetch(url)
    except Exception:                                              # noqa: BLE001
        return None
    res = parse_detail(h) if st == 200 else None
    cache.set(ck, res or {}, 24 * 60 * 60 if res else 30 * 60)
    return res


# كلماتٌ تتكرّر في كلّ إفصاحٍ فلا تميّز واحداً من آخر (قِيس: «مجلس الإدارة» ألبس
# «موافقةَ العمومية على التفويض» نصَّ «قرار المجلس بالتوزيع»)
_STOP = set(("تعلن يعلن اعلن اعلان شركه عن على في من الى مع او ثم الشركه تداول السعوديه بشان حول بخصوص "
             "لها له عبد الله مجلس اداره اداراتها ادارتها قرار المساهمين مساهمي").split())


def _tokens(s: str) -> set[str]:
    s = re.sub(r"[ً-ْـ]", "", s or "")
    s = s.translate(str.maketrans("أإآةى", "اااهي"))
    ws = {w[2:] if w.startswith("ال") and len(w) > 4 else w for w in re.findall(r"[ء-ي0-9]+", s)}
    return {w for w in ws if len(w) >= 3 and w not in _STOP}


def similar(a: str, b: str, name: str = "") -> float:
    ta, tb = _tokens(a) - _tokens(name), _tokens(b) - _tokens(name)
    if not ta or not tb:
        return 0.0
    inter = ta & tb
    return len(inter) / min(len(ta), len(tb)) if len(inter) >= 2 else 0.0


async def match(symbol: str, title: str, date: str | None, name: str = "") -> dict | None:
    """إفصاحُ «تداول» المطابقُ لإعلانٍ في التطبيق — أو None."""
    rows = await list_for(symbol)
    if not rows or not title:
        return None
    try:
        d0 = dt.date.fromisoformat((date or "")[:10])
    except ValueError:
        d0 = None
    cands = [r for r in rows if d0 is None or (r["date"] and abs((dt.date.fromisoformat(r["date"]) - d0).days) <= 3)]
    best, score = None, 0.0
    for r in cands[:6]:
        d = await detail(r["url"])
        if not d:
            continue
        s = similar(title, d["title"], name)
        if s > score:
            best, score = {**d, "url": r["url"]}, s
    # بلا تاريخٍ يُطابَق به (بعضُ إفصاحات «أرقام» تصل بلا تاريخ) يُشدَّد الحدّ
    return best if best and score >= (0.5 if d0 else 0.6) else None
