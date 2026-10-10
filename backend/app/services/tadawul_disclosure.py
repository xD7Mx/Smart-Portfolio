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
    ck = f"tadawul:annlist:v3:{sym}"          # D555: v2 يحمل TITLE — القديمُ بلا عنوانٍ فلا تُرى التوزيعات
    hit = cache.get(ck)
    if hit is not None:
        return hit
    # ‏D659: اكتشافُ نقطة البيانات في عمليّةٍ باردة قد يتعذّر أوّلَ مرّة — قِيس: «الغاز» أوّلُ رمزٍ صفرٌ وآخرُه «استحواذ ×3»
    ep = await _endpoint() or await _endpoint()
    if not ep:
        return []
    from app.services.tadawul_http import smart_fetch
    form = {"annoucmentType": "1_-1", "symbol": sym, "sectorDpId": "", "searchType": "", "fromDate": "",
            "toDate": "", "datePeriod": "", "productType": "", "advisorsList": "", "textSearch": "",
            "pageNumberDb": "1", "pageSize": str(size)}
    import json
    rows: list = []
    # ‏D659: أوّلُ طلبٍ في عمليّةٍ باردة قد يعود فارغاً (الجلسةُ لم تُدفَّأ بعد) — قِيس: «الغاز» أوّلُ رمزٍ في الفحص صفرٌ دائماً
    # والبقيّةُ تصل. وشركةٌ مدرجةٌ لا تخلو صفحتُها من إفصاح، فالفراغُ تعذّرٌ يُعاد مرّةً لا جوابٌ يُحفظ.
    for _try in range(2):
        try:
            st, raw = await smart_fetch(ep, method="POST", data=form, referer=PAGE, warm=PAGE,
                                        headers={"X-Requested-With": "XMLHttpRequest"})
            rows = (json.loads(raw) or {}).get("announcementList") or [] if st == 200 else []
        except Exception as e:                                     # noqa: BLE001
            logger.debug("إفصاحاتُ تداول لـ{}: {}", sym, e)
            rows = []
        # ‏D659: الجلسةُ الباردة تُرجع العناوينَ بالعربية (‏45 ألف حرف) والدافئةُ بالإنجليزية (‏48 ألفاً) — والمصنِّفُ يقرأ
        # الإنجليزية، فكان أوّلُ طلبٍ بعد كلّ إعادة تشغيلٍ «لا أحداث» يُحفظ يوماً (قِيس: «الغاز» صفرٌ أوّلاً وثلاثةٌ ثانياً).
        english = sum(1 for r in rows if re.search(r"[A-Za-z]{3}", str(r.get("SHORT_DESC") or r.get("TITLE") or "")))
        if rows and english * 2 >= len(rows):
            break
        if not rows:
            cache.set("tadawul:annlist:ep", None, 1)                # نقطةٌ مكتشفةٌ لا تُجيب تُكتشف من جديد قبل الإعادة
            ep = await _endpoint() or ep
    out = []
    for r in rows:
        if str(r.get("SYMBOL")) != sym or not r.get("announcementUrl"):
            continue
        out.append({"date": _date(r.get("PR_DATE")), "id": str(r.get("announcementNumber") or r.get("PRESS_REL_ID")),
                    "title": str(r.get("SHORT_DESC") or r.get("TITLE") or ""),   # D555: TITLE اسمُ الصندوق، والعنوانُ في SHORT_DESC
                    "url": O + r["announcementUrl"].replace("locale=en", "locale=ar")})
    _en = sum(1 for o in out if re.search(r"[A-Za-z]{3}", o.get("title") or ""))
    cache.set(ck, out, 60 * 60 if out and _en * 2 >= len(out) else 10 * 60)   # عناوينُ لم تصل بالإنجليزية لا تُحفظ ساعة
    return out


_AR = re.compile(r"[؀-ۿ]")


async def market_list(size: int = 150) -> list[dict]:
    """‏D670: إفصاحاتُ الشركات في السوق كلّه بعناوينها العربية الرسمية — [{symbol, company_name, title, date, url, id}].

    كانت مفكرةُ «تداول» تقرأ خدمةَ أخبار السوق (`getNewsListData`): أخبارٌ للهيئة و«إيداع» بلا رمز وبالإنجليزية،
    فأسقطها المرشِّحُ العربيّ كلَّها (قِيس: 19 في المخزن · 0 في المفكرة). والخدمةُ نفسُها التي تقرأ إفصاحاتِ الشركة
    (‏`getAnnouncementListData`) تُعطي السوقَ كلَّه برمزٍ فارغ — قِيس: 60 من 60 بعنوانٍ عربيّ ورمزٍ ورابطِ متنٍ
    في الجلسة المسخَّنة بصفحة `locale=ar`، و0 من 60 عربيةً في الجلسة الباردة. فلا ترجمةَ: النصُّ العربيُّ رسميٌّ موجود."""
    ck = "tadawul:annlist:market:v1"
    hit = cache.get(ck)
    if hit:
        return hit
    ep = await _endpoint() or await _endpoint()
    if not ep:
        return []
    from app.services.tadawul_http import smart_fetch
    import json
    form = {"annoucmentType": "1_-1", "symbol": "", "sectorDpId": "", "searchType": "", "fromDate": "",
            "toDate": "", "datePeriod": "", "productType": "", "advisorsList": "", "textSearch": "",
            "pageNumberDb": "1", "pageSize": str(size)}
    rows: list = []
    for _try in range(3):
        try:
            st, raw = await smart_fetch(ep, method="POST", data=form, referer=PAGE, warm=PAGE,
                                        headers={"X-Requested-With": "XMLHttpRequest"})
            rows = (json.loads(raw) or {}).get("announcementList") or [] if st == 200 else []
        except Exception as e:                                     # noqa: BLE001
            logger.debug("إفصاحاتُ السوق في تداول: {}", e)
            rows = []
        ar = sum(1 for r in rows if _AR.search(str(r.get("SHORT_DESC") or "")))
        if rows and ar * 2 >= len(rows):
            break
    out = []
    for r in rows:
        sym = str(r.get("SYMBOL") or "").strip()
        title = " ".join(str(r.get("SHORT_DESC") or "").split())
        d = _date(r.get("PR_DATE"))
        if not (sym.isdigit() and _AR.search(title) and d and r.get("announcementUrl")):
            continue                                               # ما لم يصل عربياً لا يُعرض — ولا يُترجَم
        out.append({"symbol": sym, "company_name": " ".join(str(r.get("TITLE") or "").split()) or None,
                    "title": title, "date": d, "date_kind": "announced",
                    "id": str(r.get("announcementNumber") or r.get("PRESS_REL_ID") or ""),
                    "url": O + r["announcementUrl"].replace("locale=en", "locale=ar")})
    if out:
        cache.set(ck, out, 30 * 60)
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


# ‏D620: حدثُ المفكرة يحمل تاريخَ وقوعه (صرفُ الأرباح، الأحقية، الجمعية) لا تاريخَ إعلانه — قِيس: «صرف أرباح نقدية»
# للراجحي في 2026/10/01 وإعلانُه في «تداول» قبلها بأسابيع، فنافذةُ ±3 أيام لا تجده ويختفي مربّعُ النصّ.
# فلهذه الأنواع: أحدثُ إعلانٍ من نوعها قبل الحدث بخمسة أشهرٍ على الأكثر.
_KINDS = (
    # ‏D665: أخبارُ المفكرة الصحفية («عموميةُ سينومي توافق…»، «هيئةُ السوق توافق على زيادة رأس مال…»، «نهايةُ أحقية أسهم
    # منحة») لا تشبه عناوينَ إفصاحاتها لفظاً، فكانت تُفتح بلا نصّ (قِيس: 11 من 11). فالأخصُّ أوّلاً، ولا يقف البحثُ
    # عند أوّل عائلةٍ لم تُطابق.
    # وعناوينُ القائمة تصل **بالإنجليزية** (D659 يطلبها كذلك لمصنِّف الأحداث) — فقِيس أنّ شرطاً عربياً وحدَه لا يطابق شيئاً
    # (11 من 11 بلا نصٍّ بعد النشر الأوّل). فلكلّ عائلةٍ لفظُها باللغتين، ويكفي أحدُهما.
    (("حقوق أولوية", "حقوق الأولوية", "نشرة الإصدار"), ("أولوية", "rights issue", "right issue", "rights offering", "priority rights")),
    (("أسهم منحة", "منحة", "زيادة رأس", "رأس المال", "رأس مال"), ("رأس المال", "capital increase", "increase capital", "increase in capital", "increase its capital", "increase the capital",
                                                                          "increasing the capital", "increasing its capital", "bonus share")),
    (("صرف", "توزيع", "أرباح نقدية", "أحقية", "احقية"), ("أرباح", "dividend")),
    (("جمعية", "عمومية"), ("جمعية", "general assembly")),
)


def kind_fallback(rows: list[dict], title: str, d0) -> dict | None:
    if d0 is None:
        return None
    for keys, need in _KINDS:
        if not any(k in (title or "") for k in keys):
            continue
        best = None
        for r in rows:
            try:
                rd = dt.date.fromisoformat(r["date"]) if r.get("date") else None
            except ValueError:
                rd = None
            if rd is None or not (d0 - dt.timedelta(days=150) <= rd <= d0 + dt.timedelta(days=3)):
                continue
            t = (r.get("title") or "").lower()
            if any(n.lower() in t for n in need) and (best is None or rd > best[0]):
                best = (rd, r)
        if best:
            return best[1]
    return None


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
    if best and score >= (0.5 if d0 else 0.6):
        return best
    fb = kind_fallback(rows, title, d0)
    if fb:
        d = await detail(fb["url"])
        if d:
            return {**d, "url": fb["url"]}
    return None
