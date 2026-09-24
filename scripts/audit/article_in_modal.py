#!/usr/bin/env python3
"""محتوى إعلان «أرقام» داخل النافذة بلا زرّ «المصدر» (D466).

    python3 scripts/audit/article_in_modal.py

طلب المالك: «الغِ زرّ المصدر واجلب محتواه بالكامل في النافذة». وقِيس أنّ
مقالات «أرقام» نوعان: مفتوحٌ يُعرض كاملاً، ومقفلٌ للمشتركين لا يُعرض منه
إلا ملخّصُه المعلن — فالنصُّ الموجَّه لمحرّكات البحث لا يُسحب (لا تجاوزَ لاشتراك).
"""
from __future__ import annotations
import os as _os, tempfile as _tf
_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX
import asyncio, pathlib, re, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend")); sys.path.insert(0, "/app")
try:
    from app.services import article_body as A, tadawul_http as T
except ModuleNotFoundError as e:
    print(f"⚠ بيئةٌ ناقصة ({e.name}) — لم يُقَس"); sys.exit(0)

BODY = ("&lt;p&gt;أعلنت الشركة عن استقالة الرئيس التنفيذي اعتباراً من تاريخه.&lt;/p&gt;"
        "&lt;p&gt;وكلّف المجلس العضو المنتدب بمهامه حتى تعيين بديل.&lt;/p&gt;"
        "&lt;table&gt;&lt;tr&gt;&lt;td&gt;البند&lt;/td&gt;&lt;td&gt;القيمة&lt;/td&gt;&lt;/tr&gt;&lt;/table&gt;")
FREE = ('<html><meta property="og:description" content="ملخص" />'
        '<script type="application/ld+json">{"@type":"NewsArticle","articleBody":"' + BODY + '"}</script></html>')
SECRET = "النصُّ الكاملُ للمشتركين فقط وفيه أرقامٌ حصرية"
LOCKED = ('<html><meta property="og:description" content="سجلت الشركة أول خسائر فصلية" />'
          '<script type="application/ld+json">{"@type":"NewsArticle","articleBody":"&lt;p&gt;' + SECRET + '&lt;/p&gt;"}</script>'
          '<div>للإستمرار في قراءة التقرير يرجي تسجيل الدخول أو اشترك معنا</div></html>')
PAGES = {"https://www.argaam.com/ar/article/articledetail/id/1": FREE,
         "https://www.argaam.com/ar/article/articledetail/id/2": LOCKED}
calls = []
async def fake(url, **k):
    calls.append(url); return 200, PAGES.get(url, "")
T.smart_fetch = fake
from app.services import cache
cache.get = lambda k: None
cache.set = lambda *a, **k: None

fail = 0
def check(ok, label, det=""):
    global fail
    if not ok: fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))

f = asyncio.run(A.read("https://www.argaam.com/ar/article/articledetail/id/1")) or {}
check("استقالة الرئيس التنفيذي" in f.get("text", "") and "العضو المنتدب" in f.get("text", "") and f.get("full") is True,
      "١ المقالُ المفتوحُ يُعرض نصُّه كاملاً", f.get("text", "")[:60])
check("\n" in f.get("text", "") and "<" not in f.get("text", "") and "البند | القيمة" in f.get("text", ""),
      "٢ بفقراته وجدوله نصّاً مقروءاً بلا وسوم")
l = asyncio.run(A.read("https://www.argaam.com/ar/article/articledetail/id/2")) or {}
check(SECRET not in l.get("text", "") and l.get("text") == "سجلت الشركة أول خسائر فصلية" and l.get("full") is False,
      "٣ والمقفلُ للمشتركين لا يُسحب نصُّه الخفيّ — ملخّصُه المعلنُ وحده", l.get("text", "")[:60])
n = len(calls)
for bad in ("https://evil.example/ar/article/articledetail/id/1", "http://www.argaam.com/ar/article/articledetail/id/1",
            "https://www.argaam.com/ar/company/companyoverview/marketid/3/companyid/911"):
    asyncio.run(A.read(bad))
check(len(calls) == n, "٤ ولا يُجلب إلا مقالُ «أرقام» (لا مضيفَ آخر ولا صفحةَ شركة)")
ev = (ROOT / "frontend/src/components/market/EventsList.tsx").read_text(encoding="utf-8")
modal = ev[ev.index("function EventDetailModal"):ev.index("function", ev.index("function EventDetailModal") + 30)]
check("المصدر\n" not in modal and "resolveNewsUrl" not in modal and "articleBody(" in modal and "<ArgaamButton" in modal,
      "٥ النافذةُ بلا زرّ «المصدر»، تجلب المحتوى، وزرُّ أرقام باقٍ")
print(f"{'FAIL' if fail else 'PASS'} D466 — محتوى الإعلان داخل النافذة")
sys.exit(fail)
