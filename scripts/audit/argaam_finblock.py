#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# أين يسكن جدولُ «المؤشرات المالية» في «أرقام»؟ — **مسبارُ موضعٍ لا محلّل**.
#
# ## ما قِيس قبله
# طُبعت صفوفُ صفحة الشركة كاملةً (‏36 صفّاً) فلم يكن فيها صفُّ مؤشرٍ واحد:
# لا مكرّرَ ربحيةٍ ولا قيمةً دفترية. والعنوانُ «المؤشرات المالية» مكتوبٌ في
# الصفحة — فالقسمُ موجودٌ ومحتواه يُجلَب بنداءٍ منفصل بعد فتح الصفحة.
#
# ## ما يفعله هذا
# ثلاثةُ أسئلةٍ بترتيبها، ولا يُبنى على ظنّ:
#   ١· ما الترميزُ المحيط بالعنوان؟ (يُطبع خاماً — منه يُعرف اسمُ النداء)
#   ٢· ما نداءاتُ الجلب المذكورةُ في الصفحة؟ (‏ajax · partial · url:)
#   ٣· أتردّ المساراتُ المرشّحةُ جدولاً فيه أرقام؟ (تُجرَّب ويُطبع ردُّها)
#
#   docker exec sp_backend python /app/scripts/audit/argaam_finblock.py
#   docker exec sp_backend python /app/scripts/audit/argaam_finblock.py 1120
#
# لا يكتب شيئاً ولا يغيّر إعداداً. وما ردَّ ‎404 يُقال ‎404 — لا يُفسَّر بأن
# «الشركة بلا مؤشرات».
# ─────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import os as _os, shutil as _sh, tempfile as _tf
_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
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

SAMPLE = ["1120", "4190"]          # بنكٌ وتجزئة — يكفيان لكشف اسم النداء

_FIN = re.compile(r"المؤشرات\s*المالية")
# مساراتٌ مرشّحةٌ على منوال ما عرفناه من «أرقام» (‏_REC_PATHS): اسمُ القسم
# في المسار، والسوقُ ‎3 والمعرّفُ في الذيل. تُجرَّب ولا تُفترض.
_CAND = (
    "/ar/company/financialratios/marketid/3/companyid/{cid}",
    "/ar/company/companyratios/marketid/3/companyid/{cid}",
    "/ar/company/financialindicators/marketid/3/companyid/{cid}",
    "/ar/company/indicators/marketid/3/companyid/{cid}",
    "/ar/company/keyratios/marketid/3/companyid/{cid}",
    "/ar/company/ratios/marketid/3/companyid/{cid}",
    "/ar/company/companyfinancialratio/marketid/3/companyid/{cid}",
)


def _plain(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s)).strip()


async def one(sym: str) -> None:
    from app.services.argaam_calendar import (_company_id, _company_url, UA,
                                              _rows_of, BASE)
    import httpx

    print(f"\n■ {sym}")
    cid = await _company_id(sym)
    if not cid:
        print("   لا معرّفَ للشركة في أرقام.")
        return

    async with httpx.AsyncClient(timeout=30, follow_redirects=True,
                                 headers={"User-Agent": UA,
                                          "Accept-Language": "ar,en;q=0.8"}) as c:
        try:
            r = await c.get(_company_url(cid))
        except Exception as e:                                    # noqa: BLE001
            print(f"   تعذّر الجلب ({type(e).__name__})")
            return
        if r.status_code != 200:
            print(f"   ‎{r.status_code} من صفحة الشركة.")
            return
        page = r.text

        # ١· الترميزُ حول العنوان — خاماً. منه يُقرأ اسمُ الحاوية ومعرّفُها،
        #    وهما ما يستدعيه سكربتُ الصفحة.
        print("   ── الترميزُ حول العنوان ──")
        for i, m in enumerate(_FIN.finditer(page)):
            if i >= 2:
                break
            a, b = max(0, m.start() - 420), m.start() + 420
            snip = re.sub(r"\s+", " ", page[a:b])
            print(f"     [{i + 1}] …{snip}…")

        # ٢· نداءاتُ الجلب المذكورةُ في الصفحة — تُصفّى بألفاظ القسم.
        urls = set(re.findall(r'["\'](/[A-Za-z0-9/_\-.{}]+)["\']', page))
        interesting = sorted(u for u in urls if re.search(
            r"ratio|indicator|financial|partial|keyfig|summary", u, re.I))
        print(f"   ── مساراتٌ في الصفحة تحمل لفظَ القسم: {len(interesting)} ──")
        for u in interesting[:15]:
            print("     · " + u)

        # ٣· المساراتُ المرشّحة — تُجرَّب ويُقال ردُّها بنصّه.
        print("   ── تجربةُ المرشّحات ──")
        for path in _CAND:
            url = BASE + path.format(cid=cid)
            try:
                x = await c.get(url)
            except Exception as e:                                # noqa: BLE001
                print(f"     {path.split('/')[3]:<26} خطأ {type(e).__name__}")
                continue
            if x.status_code != 200:
                print(f"     {path.split('/')[3]:<26} ‎{x.status_code}")
                continue
            rows = _rows_of(x.text)
            nums = len(re.findall(r"\d+[.,]\d{1,2}", _plain(x.text)))
            print(f"     {path.split('/')[3]:<26} ‎200 · صفوف {len(rows)} · أرقام {nums}")
            for cells in rows[:8]:
                print("        · " + " | ".join(cc[:30] for cc in cells[:6]))


async def main() -> int:
    syms = [a.replace(".SR", "") for a in sys.argv[1:] if not a.startswith("-")] or SAMPLE
    print("مسبارُ موضعٍ لجدول «المؤشرات المالية» — يعرض ما وصل، ولا يبني محلّلاً.")
    print("─" * 74)
    for s in syms:
        try:
            await one(s)
        except Exception as e:                                    # noqa: BLE001
            print(f"\n■ {s}\n   انقطع الفحص ({type(e).__name__}: {e})")
    print("\n" + "─" * 74)
    print("إن ظهر مسارٌ يردّ صفوفاً بأرقام، بُني عليه المحلّل. وإلا فالقسمُ")
    print("يُملأ بجافاسكربت ولا يُقرأ من الترميز — ويُقال ذلك ولا يُلتَفّ عليه.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
