#!/usr/bin/env python3
"""دليلُ «أرقام» — قطاعاتٌ ورموزٌ صحيحة، مرجعٌ إرشاديٌّ لا يُكتب في التطبيق.

    docker exec sp_backend python /app/scripts/audit/argaam_directory.py
    docker exec sp_backend python /app/scripts/audit/argaam_directory.py "<رابط>"
    docker exec sp_backend python /app/scripts/audit/argaam_directory.py --save

بأمر المالك: «ابحث عن الدليل، وعندما تجده يكون لدينا أسماءُ القطاعات
والرموزُ الصحيحة، ثمّ نأخذ ما يحتاجه محرّكُ الجودة ومحرّكُ السعر العادل
من بياناتٍ ماليةٍ من تداول أو أرقام». وقال قبلَها: «اجعل الدليلَ دليلاً
إرشادياً لك» — فلا يُكتب في `MARKET_UNIVERSE` ولا يمسّ المحفظة.

## المنهج: يُحكَم بمعيارٍ لا بحظّ

محاولتي الأولى دخلت صفحاتَ شركاتٍ فردية (`companyoverview/marketid/3/…`)
فقرأت عناوينَ أخبارٍ كأنها رموزاً (‏D390) — لأني حكمتُ على الصفحة
بوجود «رقمٍ رباعيّ» فيها، وذاك يصف الخبرَ كما يصف الرمز. فالمعيارُ
الآن **ثلاثيٌّ ومعلَن**:

  ١· الرمزُ يُقرأ من **مسارِ رابطِ شركةٍ** (`/company/…/<رمز>` أو
     `companyid/<n>`) أو من خليّةٍ **كلُّها** أربعةُ أرقام — لا من نصٍّ
     طويلٍ فيه رقم.
  ٢· ويُشترط أن يكون في نطاق السوق الرئيسيّ (‏1000–8999) — ورموزُ
     ‎9xxx «نمو» تُعَدّ وتُستثنى بأمر المالك.
  ٣· وتُطابَق أسماءُ القطاعات على أسماء قطاعاتنا الاثنين والعشرين —
     فصفحةٌ فيها رموزٌ بلا أسماءِ قطاعاتٍ ليست دليلاً بل جدولَ أسعار.

والمرشَّحُ الأعلى في المعيار يُطبَع مفصَّلاً: القطاعُ وأعضاؤه، ثمّ
يُقارَن بدليلنا **بأسماء الفروق لا بعددها**، ويُحفَظ مرجعاً في `docs/`
مع تاريخِ جلبه بـ`--save`.
"""
from __future__ import annotations

import asyncio
import json
import re
import sys
from collections import Counter
from datetime import date

sys.path.insert(0, "/app")
sys.path.insert(0, "backend")

SAVE = "--save" in sys.argv
DUMP = "--dump" in sys.argv
GIVEN = [a for a in sys.argv[1:] if a.startswith("http")]
BASE = "https://www.argaam.com"
HOME = f"{BASE}/ar"

# مساراتٌ مرشَّحةٌ — تُجرَّب كلُّها ويُحكَم بالمعيار لا بالاسم
PATHS = (
    "/ar/company/companies-prices/3",
    "/ar/company/companies-prices/3/",
    "/ar/companies/3",
    "/ar/company/sectors/3",
    "/ar/company/all-companies/3",
    "/ar/company/companies/3",
    "/ar/market/tasi",
    "/ar/tadawul/tasi",
    "/ar/company/companies-prices",
)
_TR = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S | re.I)
_TD = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.S | re.I)
_TAG = re.compile(r"<[^>]+>")
_A = re.compile(r"""<a\b[^>]*href=["']([^"']+)["'][^>]*>(.*?)</a>""",
                re.S | re.I)
_CODE_IN_HREF = re.compile(r"/(\d{4})(?:[/?#]|$)")
_CID = re.compile(r"companyid/(\d+)", re.I)
_CELL_CODE = re.compile(r"^\(?(\d{4})\)?$")
# نصُّ رابطِ الشركة في دليل «أرقام»: «2330 - المتقدمة» (D394)
_LABEL_CODE = re.compile(r"^\(?(\d{4})\)?\s*[-–—:]\s*(.+)$")


def _txt(x: str) -> str:
    return re.sub(r"\s+", " ", _TAG.sub(" ", x or "")).strip()


def _main_code(c: str) -> str | None:
    """رمزٌ في نطاق السوق الرئيسيّ — و‎9xxx يُعَدّ نمو فيُستثنى."""
    if not c or len(c) != 4 or not c.isdigit():
        return None
    return c if "1000" <= c <= "8999" else None


async def main() -> int:
    from app.data.market_universe import MARKET_UNIVERSE
    from app.data.universe import main_market
    from app.services.tadawul_http import smart_fetch

    ours = main_market(MARKET_UNIVERSE)
    our_secs = {(m or {}).get("sector") for m in ours.values()}
    our_secs.discard(None)
    print(f"═ دليلُ «أرقام» ═ دليلُنا: {len(ours)} شركة · "
          f"{len(our_secs)} قطاعاً")

    async def get(u: str):
        try:
            st, body = await smart_fetch(u, warm=HOME, timeout=25)
            return st, body or ""
        except Exception as e:                                    # noqa: BLE001
            return 0, f"__ERR__{type(e).__name__}"

    urls = GIVEN or [BASE + p for p in PATHS]
    best: tuple[int, str, dict] | None = None
    for u in urls:
        st, body = await get(u)
        if body.startswith("__ERR__") or st != 200 or not body:
            print(f"  ✗ {u[-52:]}: {st}{' · ' + body[7:] if body.startswith('__ERR__') else ''}")
            continue
        # ══ والرمزُ في **نصّ** الرابط لا في مساره ══ (D394)
        # قِيس على خادم المالك: خرج «1007=2330 - المتقدمة» — فـ1007
        # معرِّفُ «أرقام» في المسار، والرمزُ الحقيقيُّ 2330 مكتوبٌ في نصّ
        # الرابط بصيغة «رمز - اسم». فقرأتُ معرِّفاً وظننتُه رمزاً، فخرج
        # «366 رمزاً» و«120 عندهم وليس عندنا» — وكلُّها وهمُ قراءة.
        # فالرمزُ يُقرأ من النصّ، والمعرِّفُ من المسار — وكلٌّ يُسمّى باسمه.
        codes: dict[str, str] = {}          # رمز → اسم
        cids: dict[str, str] = {}           # رمز → معرِّفُ أرقام
        pos: dict[str, int] = {}            # رمز → موضعُه في الصفحة
        for m in _A.finditer(body):
            href, label = m.group(1), _txt(m.group(2))
            mm = _LABEL_CODE.match(label)
            if not mm:
                continue
            code = _main_code(mm.group(1))
            if not code:
                continue
            nm = mm.group(2).strip()
            if nm and code not in codes:
                codes[code] = nm
                pos[code] = m.start()
                c = _CID.search(href)
                if c:
                    cids[code] = c.group(1)
        nomu = len({mm.group(1) for _h, _l in _A.findall(body)
                    for mm in [_LABEL_CODE.match(_txt(_l))]
                    if mm and mm.group(1).startswith("9")})
        # ٣· أسماءُ قطاعاتٍ تُطابق قطاعاتنا
        secs_hit = sorted(s for s in our_secs if s and s in body)
        score = len(codes) + 10 * len(secs_hit)
        print(f"  {'★' if score else '·'} {u[-52:]}: {len(body)} حرفاً"
              f" · رموزٌ رئيسية={len(codes)} · نمو={nomu}"
              f" · قطاعاتٌ مطابقة={len(secs_hit)} · معرِّفاتُ أرقام={len(cids)}"
              f" · وزنٌ={score}")
        # ══ ونسبةُ الشركة إلى قطاعها تُقرأ من بنيةِ الصفّ ══ (D395)
        #
        # قِيس على خادم المالك أن منهجي الأوّل باطل: أخذتُ «أقربَ اسمِ
        # قطاعٍ يسبق الشركة» فنُسبت 1201 و2010 و2150 و3002 كلُّها إلى
        # «الطاقة» وفيها إسمنتٌ وأغذية — لأن الصفحةَ تحمل أسماءَ القطاعات
        # في **قائمة تصفيةٍ أعلاها**، فما بعد أوّل اسمٍ يُنسَب إليه.
        # فقرينةُ الموضع لا تصلح، ويُقرأ القطاعُ من **خلايا صفّ الشركة**:
        # خليّةٌ نصُّها اسمُ قطاعٍ من قطاعاتنا. وما لم يُوجَد في صفّه
        # يبقى **بلا قطاع** ولا يُخمَّن — فنسبةٌ خاطئةٌ تُقاس بمسطرةٍ
        # ليست لها، وذاك أسوأُ من غيابها.
        of_sec: dict[str, str] = {}
        if DUMP:
            print("   ── بنيةُ أوّل ثلاثةِ صفوفٍ فيها رابطُ شركة ──")
        shown = 0
        for tr in _TR.findall(body):
            cells = [_txt(c) for c in _TD.findall(tr)]
            if not cells:
                continue
            code = None
            for m2 in _A.finditer(tr):
                mm2 = _LABEL_CODE.match(_txt(m2.group(2)))
                if mm2 and _main_code(mm2.group(1)):
                    code = mm2.group(1)
                    break
            if not code:
                continue
            if DUMP and shown < 3:
                shown += 1
                print(f"      {code}: {cells[:10]}")
            sec = next((c for c in cells if c in our_secs), None)
            if sec:
                of_sec[code] = sec
        if best is None or score > best[0]:
            best = (score, u, {"codes": codes, "cids": cids,
                               "secs": secs_hit, "of_sec": of_sec,
                               "body_len": len(body)})

    if not best or not best[2]["codes"]:
        print("\n✗ لم يُعثَر على دليلٍ يجتاز المعيار. وهذا **ليس نفياً**"
              " لوجوده: يُجرَّب رابطٌ يُمرَّر بالوسيط، أو يُقرأ من قائمة"
              " تنقّل الموقع. ولا يُبنى دليلٌ على صفحةٍ لم تجتز.")
        return 1

    score, url, data = best
    codes, cids, secs = data["codes"], data["cids"], data["secs"]
    print(f"\n═ المرشَّحُ الأعلى ═ {url}\n  وزنٌ={score}"
          f" · رموزٌ={len(codes)} · قطاعاتٌ={len(secs)}")
    if secs:
        print("  قطاعاتٌ ظهرت بأسمائها: " + " · ".join(secs[:24]))

    # ── المقارنةُ بدليلنا: بالأسماء لا بالعدد ──────────────────────────
    theirs = set(codes)
    mine = set(ours)
    print(f"\n═ المقارنة ═ عندهم {len(theirs)} · عندنا {len(mine)}")
    add = sorted(theirs - mine)
    gone = sorted(mine - theirs)
    print(f"  عندهم وليس عندنا ({len(add)}): "
          + (" · ".join(f"{c}={codes[c][:18]}" for c in add[:14]) or "لا شيء"))
    print(f"  عندنا وليس عندهم ({len(gone)}): "
          + (" · ".join(f"{c}={(ours[c] or {}).get('name_ar') or ''}"[:22]
                        for c in gone[:14]) or "لا شيء"))
    # ══ اختلافُ نسبةِ الشركة إلى قطاعها ══ (أثمنُ ما في الدليل)
    of_sec = data.get("of_sec") or {}
    if of_sec:
        cnt: Counter = Counter(of_sec.values())
        print("\n═ قسمةُ «أرقام» على القطاعات ═")
        for k, v in cnt.most_common():
            print(f"  {v:>3}  {k}")
        mism = [(c, of_sec[c], (ours[c] or {}).get("sector"))
                for c in sorted(set(of_sec) & set(ours))
                if (ours[c] or {}).get("sector")
                and of_sec[c] != (ours[c] or {}).get("sector")]
        print(f"\n═ شركاتٌ قطاعُها عندنا يخالف «أرقام» ═ {len(mism)}")
        for c, thr, our in mism[:24]:
            print(f"  {c} · أرقام: {thr} ≠ عندنا: {our}")
    if secs:
        diff = []
        for c in sorted(theirs & mine):
            our_s = (ours[c] or {}).get("sector")
            if our_s and our_s not in secs:
                diff.append(f"{c}:{our_s}")
        print(f"  ولنا قطاعاتٌ لم تظهر في صفحتهم: {len(set(diff))}"
              + (" · " + " · ".join(sorted({d.split(':')[1] for d in diff})[:6])
                 if diff else ""))

    if SAVE:
        import pathlib
        out = {
            "المصدر": url,
            "تاريخُ الجلب": date.today().isoformat(),
            "ملاحظة": ("مرجعٌ إرشاديٌّ فقط — لا يُكتب في دليل التطبيق"
                       " ولا يمسّ المحفظة (بأمر المالك)"),
            "رموزٌ": {c: {"name": n, "argaam_id": cids.get(c)}
                      for c, n in sorted(codes.items())},
            "قطاعاتٌ ظهرت": secs,
            "قطاعُ كلّ شركة": data.get("of_sec") or {},
        }
        p = pathlib.Path("/app/docs/ARGAAM_DIRECTORY.json")
        if not p.parent.exists():
            p = pathlib.Path("docs/ARGAAM_DIRECTORY.json")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(out, ensure_ascii=False, indent=1), "utf-8")
        print(f"\n  حُفظ مرجعاً: {p} ({len(codes)} رمزاً)")

    print("\nالحكم: الدليلُ يُقبَل حين يجتاز المعيارَ الثلاثيَّ — رموزٌ من"
          " مسارات روابطِ شركاتٍ، في نطاق الرئيسيّ، ومعها أسماءُ قطاعاتٍ."
          " ويبقى **مرجعاً إرشادياً**: تُقرأ منه أسماءُ القطاعات ونسبةُ"
          " كلّ شركةٍ إلى قطاعها (وهو أثمنُ ما فيه، لأن الخريطةَ تُطبَّق"
          " بالقطاع فشركةٌ في قطاعٍ خطأ تُقاس بمسطرةٍ ليست لها)، ولا"
          " يُكتب في دليل التطبيق إلا بأمرٍ صريح.")
    return 0


raise SystemExit(asyncio.run(main()))
