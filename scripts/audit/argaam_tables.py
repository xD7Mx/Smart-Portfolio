#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# جدولا «أرقام» — **مسبارُ شكلٍ لا محلّل**.
#
# ## لماذا مسبارٌ أوّلاً
# في صفحة الشركة بـ«أرقام» جدولان: «أداء السهم» (نظرةٌ فنّية) و«المؤشرات
# المالية» (نظرةٌ أساسية). والثاني هو ما يُبنى عليه تقييمٌ نسبيٌّ إلى
# القطاع يملأ فراغَ تقدير المحلّلين في ‎124 شركةً لا يغطّيها بيتُ خبرة.
#
# ولا يُكتب محلّلٌ لجدولٍ لم يُرَ شكلُه. تخمينُ تخطيط الجدول من بعيد هو
# بعينه ما أوقعنا في أخطاءٍ سابقة (‏D-أرقام/توصيات). فهذا يطبع **العناوينَ
# والخلايا الخام كما وصلت**، ومنها يُبنى المحلّلُ على الشكل الحقيقيّ.
#
#   docker exec sp_backend python /app/scripts/audit/argaam_tables.py
#   docker exec sp_backend python /app/scripts/audit/argaam_tables.py 2222 4340
#
# لا يكتب شيئاً ولا يغيّر إعداداً — يقرأ ويطبع. وما لم يُقَس لا يُدَّعى:
# إن ردّ المصدرُ ‎403 أو خلت الصفحةُ من الجدول قيل ذلك بنصّه، ولا يُفسَّر
# بأن «الشركة بلا مؤشرات».
# ─────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import os as _os, shutil as _sh, tempfile as _tf
_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
# الرملةُ تمنع الكتابةَ في مخزن التشغيل، والنسخُ يُبقي القراءةَ صادقة —
# رملةٌ فارغةٌ أعمت مسباراً سابقاً فأعلن عمى قراءته حكماً على السوق.
_REAL_LG = _os.environ.get("LASTGOOD_PATH") or (
    "/app/data/lastgood.json" if _os.path.isdir("/app/data") else "")
_COPY = _os.path.join(_SANDBOX, "lastgood.json")
if _REAL_LG and _os.path.exists(_REAL_LG):
    try:
        _sh.copyfile(_REAL_LG, _COPY)
    except Exception:                                             # noqa: BLE001
        pass
_os.environ["LASTGOOD_PATH"] = _COPY
_os.environ["SP_STATE_DIR"] = _SANDBOX

import asyncio
import re
import sys

for _p in ("/app", "backend", "."):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# عيّنةٌ من قطاعاتٍ مختلفة — بنكٌ وطاقةٌ وبتروكيماوياتٌ وتجزئةٌ ومرافقُ
# واتّصالاتٌ وصحّةٌ وأسمنتٌ وتأمينٌ وريت. فشكلُ الجدول قد يختلف باختلاف
# القطاع، ومسبارٌ على بنوكٍ وحدَها يُنتج محلّلاً ينكسر على أوّل ريت.
SAMPLE = ["1120", "2222", "2010", "4190", "5110",
          "7010", "4013", "3030", "8010", "4330"]

# عناوينُ الأقسام كما تُكتب في الصفحة — تُطابَق على النصّ العربيّ.
_H_PERF = re.compile(r"أداء\s*السهم")
_H_FIN = re.compile(r"(المؤشرات\s*المالية|المؤشرات\s*المالي)")
_HEADING = re.compile(r"<h[1-6][^>]*>(.*?)</h[1-6]>|"
                      r'<div[^>]*class="[^"]*(?:title|header|panel-heading)[^"]*"[^>]*>(.*?)</div>',
                      re.S | re.I)


def _plain(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s)).strip()


async def one(sym: str) -> None:
    from app.services.argaam_calendar import (_company_id, _company_url, UA,
                                              _rows_of)
    import httpx

    cid = await _company_id(sym)
    print(f"\n■ {sym}")
    if not cid:
        print("   لا معرّفَ للشركة في أرقام — لا حكمَ على جدولها.")
        return
    url = _company_url(cid)
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True,
                                     headers={"User-Agent": UA,
                                              "Accept-Language": "ar,en;q=0.8"}) as c:
            r = await c.get(url)
    except Exception as e:                                        # noqa: BLE001
        print(f"   تعذّر الجلب ({type(e).__name__}) · {url}")
        return
    if r.status_code != 200:
        print(f"   ‎{r.status_code} من {url}")
        return
    page = r.text

    # أوّلاً: أفي الصفحة قسمان بهذين الاسمين أصلاً؟ يُقال ما وُجد وما غاب.
    flat = _plain(page)
    print(f"   القسمان : أداء السهم {'موجود' if _H_PERF.search(flat) else 'غائب'}"
          f" · المؤشرات المالية {'موجود' if _H_FIN.search(flat) else 'غائب'}")
    heads = [_plain(m.group(1) or m.group(2) or "") for m in _HEADING.finditer(page)]
    heads = [h for h in heads if 2 < len(h) < 60][:14]
    print(f"   عناوينُ الصفحة: {heads}")

    rows = _rows_of(page)
    print(f"   صفوفٌ مقروءة: {len(rows)}")
    # الخلايا الخام: صفوفٌ قصيرةٌ (تسميةٌ + قيمة) هي شكلُ لوحةِ المؤشرات
    # غالباً، والطويلةُ جداولُ بيانات. يُعرض الصنفان بلا تصنيفٍ مسبق —
    # التصنيفُ حكمٌ، والمسبارُ يعرض ولا يحكم.
    for cells in rows[:22]:
        print("     · " + " | ".join(c[:34] for c in cells[:7]))
    if len(rows) > 22:
        print(f"     … و{len(rows) - 22} صفّاً آخر.")

    # أرقامٌ في الصفحة أصلاً؟ صفحةٌ بلا رقمٍ تُملأ بجافاسكربت غالباً،
    # وذلك يقرّر أيَّ طبقةِ جلبٍ تُبنى: قراءةُ HTML أم نقطتُها الداخلية.
    nums = re.findall(r"\d+[.,]\d{1,2}", flat)
    js = bool(re.search(r"__NEXT_DATA__|/api/|ajax", page, re.I))
    print(f"   أرقامٌ في النصّ: {len(nums)}"
          + ("  ⚠ الصفحةُ تُملأ بجافاسكربت غالباً" if len(nums) < 10 and js else ""))
    print(f"   {url}")


async def main() -> int:
    args = [a.replace(".SR", "") for a in sys.argv[1:] if not a.startswith("-")]
    syms = args or SAMPLE
    print("مسبارُ شكلٍ لجدولَي «أرقام» — يعرض ما وصل، ولا يبني محلّلاً.")
    print("─" * 74)
    for s in syms:
        try:
            await one(s)
        except Exception as e:                                    # noqa: BLE001
            print(f"\n■ {s}\n   انقطع الفحص ({type(e).__name__}: {e})")
    print("\n" + "─" * 74)
    print("على شكل هذه الخلايا يُبنى المحلّل — لا على تخمينٍ لتخطيط الجدول.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
