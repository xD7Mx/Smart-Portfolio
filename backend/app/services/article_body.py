"""نصُّ إعلانات «أرقام» داخل نافذة الإعلان (D466).

طلب المالك ألّا يخرج من التطبيق: يُلغى زرُّ «المصدر» ويُعرض محتواه في
النافذة. وقِيس (`announcement_body_door.py`) أنّ الإعلانات كلَّها من مقالات
«أرقام»، وأنّ الجلبَ الذكيَّ يفتحها، وأنّها نوعان:

  · **مفتوحٌ للزائر** (إفصاحاتُ الشركات غالباً): يُعرض نصُّه كاملاً.
  · **مقفلٌ للمشتركين** (تقاريرُ أرقام): الزائرُ يرى فقرتَه الأولى ثم
    «للاستمرار في قراءة التقرير يرجى تسجيل الدخول أو اشترك». ونصُّه الكامل
    في الصفحة موجَّهٌ لمحرّكات البحث — وسحبُه تجاوزٌ لاشتراكٍ مدفوع، وقد رُفض.
    فيُعرض ما تنشره «أرقام» للجميع فقط: ملخّصُها المعلن.

ولا يُجلب إلا من «أرقام» (حمايةٌ من توجيه الخادم لعناوينَ أخرى).
"""
from __future__ import annotations
import html as _html
import json
import re
from urllib.parse import urlparse

from app.services import cache

LOCK = "للإستمرار في قراءة"
_ARTICLE = re.compile(r"^/ar/article/articledetail/id/\d+/?$")
_LD = re.compile(r"<script[^>]*application/ld\+json[^>]*>(.*?)</script>", re.S)


def allowed(url: str) -> bool:
    try:
        p = urlparse(url)
    except Exception:
        return False
    return p.scheme == "https" and p.hostname in ("www.argaam.com", "argaam.com") and bool(_ARTICLE.match(p.path))


def html_to_text(fragment: str) -> str:
    """فقراتٌ وأسطرٌ وجداولُ نصّاً مقروءاً — بلا وسومٍ ولا أنماط."""
    s = _html.unescape(fragment or "")
    s = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", s, flags=re.S | re.I)
    s = re.sub(r"</t[dh]>\s*<t[dh][^>]*>", " | ", s, flags=re.I)
    s = re.sub(r"<br\s*/?>|</(p|div|li|tr|h[1-6])>", "\n", s, flags=re.I)
    s = re.sub(r"<li[^>]*>", "• ", s, flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    s = _html.unescape(s).replace("\xa0", " ")
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in s.split("\n")]
    out, blank = [], False
    for ln in lines:
        if ln:
            out.append(ln); blank = False
        elif not blank and out:
            out.append(""); blank = True
    return "\n".join(out).strip()


def _meta(h: str, prop: str) -> str:
    m = re.search(rf'property="{prop}"\s+content="([^"]*)"', h)
    return _html.unescape(m.group(1)).strip() if m else ""


def _ld_body(h: str) -> str:
    for blk in _LD.findall(h):
        try:
            j = json.loads(blk, strict=False)
        except Exception:
            continue
        for o in (j if isinstance(j, list) else [j]):
            if isinstance(o, dict) and isinstance(o.get("articleBody"), str) and o["articleBody"].strip():
                return o["articleBody"]
    return ""


def parse(h: str) -> dict | None:
    """الصفحةُ ← {text, full}. المقفلُ يُردّ ملخّصُه المعلنُ وحده (full=False)."""
    if not h:
        return None
    if LOCK in h:
        lead = _meta(h, "og:description")
        return {"text": lead, "full": False} if lead else None
    body = html_to_text(_ld_body(h))
    if len(body) < 40:
        return None
    return {"text": body, "full": True}


async def read(url: str) -> dict | None:
    if not allowed(url):
        return None
    ck = f"argaam:article:{url}"
    hit = cache.get(ck)
    if hit is not None:
        return hit or None
    from app.services.tadawul_http import smart_fetch
    try:
        st, h = await smart_fetch(url, warm="https://www.argaam.com/", timeout=25)
    except Exception:
        return None
    res = parse(h) if st == 200 else None
    cache.set(ck, res or {}, 24 * 60 * 60 if res else 30 * 60)
    return res
