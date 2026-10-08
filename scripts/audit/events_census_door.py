#!/usr/bin/env python3
"""تعدادُ الأحداث الجوهرية من إفصاحات «تداول» لاثني عشر شهراً — اختبارُ فرضية المالك: «حصرنا الشركةَ مالياً
وظلمناها إخبارياً». لكلّ شركةٍ في القطاعات الساقطة: العقودُ وقيمُها المفصَح عنها، والاستحواذات، والجزاءات
والسلبيات — مقابل بُعد قيمتنا وبُعد السعر عن هدف المحلّلين. قارئٌ فقط: لا يمسّ رقماً منشوراً."""
import asyncio, datetime as dt, re, sys
sys.path.insert(0, "/app")
from app.data.market_universe import MARKET_UNIVERSE
from app.data.universe import main_market
from app.services.content_engine import fund_store_load
from app.services.market_screener import get_cached_screener
from app.services.tadawul_disclosure import list_for, detail

SECTORS = ("إدارة وتطوير العقارات", "السلع الرأسمالية", "التطبيقات وخدمات التقنية",
           "الخدمات الاستهلاكية", "الطاقة", "التأمين")
# ‏عناوينُ القائمة تصل بالإنجليزية (حقلُ SHORT_DESC) والمتنُ بالعربية — قِيس: صفرٌ مصنَّفٌ في 70 شركةً بأنماطٍ عربية
_FIN = re.compile(r"facilit|financing|loan|sukuk|murabaha|تسهيلات|تمويل", re.I)
KINDS = (
    ("عقد", re.compile(r"contract|award|purchase order|signing of an? (?:agreement|memorandum)|توقيع|ترسية|عقد\s+(?:مع|لتوريد|لتنفيذ)", re.I)),
    ("استحواذ", re.compile(r"acqui|merger|purchase of (?:a )?stake|استحواذ|اندماج", re.I)),
    ("سلبي", re.compile(r"violation|penalt|\bfine[sd]?\b|lawsuit|court|ruling|suspen|qualified|going concern|accumulated loss|"
                        r"resign|terminat|cancel|liquidat|مخالفة|غرامة|لجنة\s+الفصل|تعليق|خسائر\s+متراكمة|استقالة", re.I)),
)


_AR = str.maketrans("٠١٢٣٤٥٦٧٨٩٫٬", "0123456789.,")
_MULT = (("مليار", 1e9), ("مليون", 1e6), ("ألف", 1e3), ("الف", 1e3))


def money(text: str) -> float | None:
    """أكبرُ مبلغٍ في سطرٍ يذكر «قيمة» — بالريال. لا يُخمَّن: ما لا رقمَ صريحاً له لا يُعدّ."""
    best = None
    for ln in (text or "").translate(_AR).split("\n"):
        if "قيمة" not in ln and "إجمالي" not in ln:
            continue
        for m in re.finditer(r"(\d[\d,]*(?:\.\d+)?)\)?\s*(مليار|مليون|ألف|الف)?", ln):
            try:
                v = float(m.group(1).replace(",", ""))
            except ValueError:
                continue
            v *= dict(_MULT).get(m.group(2) or "", 1)
            if v >= 1e6 and (best is None or v > best):
                best = v
    return best


async def main():
    uni = main_market(MARKET_UNIVERSE)
    store = fund_store_load()
    rows = {str(r.get("symbol")).replace(".SR", ""): r for r in (get_cached_screener() or [])}
    since = (dt.date.today() - dt.timedelta(days=365)).isoformat()
    for sec in SECTORS:
        print(f"\n══ {sec}")
        for s, meta in uni.items():
            if (meta.get("sector_ar") or meta.get("sector")) != sec:
                continue
            r = rows.get(s) or {}
            fv, at, px, mc = (store.get(s) or {}).get("fair_value"), r.get("analyst_target"), r.get("price"), r.get("market_cap")
            try:
                anns = [a for a in await list_for(s, 60) if (a.get("date") or "") >= since]
            except Exception as e:                                # noqa: BLE001
                print(f"  {s} تعذّرت الإفصاحات: {e}")
                continue
            cnt = {k: [] for k, _ in KINDS}
            for a in anns:
                t = a.get("title") or ""
                for k, rx in KINDS:
                    if k == "عقد" and _FIN.search(t):
                        continue
                    if rx.search(t):
                        cnt[k].append(a)
                        break
            total = 0.0
            for a in cnt["عقد"][:12]:
                d = await detail(a["url"]) or {}
                v = money(d.get("text") or "")
                if v:
                    total += v
            dev = f"{fv/at-1:+.0%}" if isinstance(fv, (int, float)) and isinstance(at, (int, float)) and at else "—"
            pdev = f"{px/at-1:+.0%}" if isinstance(px, (int, float)) and isinstance(at, (int, float)) and at else "—"
            share = f"{total/mc:.0%} من القيمة السوقية" if total and isinstance(mc, (int, float)) and mc else ""
            neg = " | ".join((a.get("title") or "")[:90] for a in cnt["سلبي"][:3])
            con = " | ".join((a.get("title") or "")[:90] for a in cnt["عقد"][:3])
            print(f"  {s} {meta.get('name_ar')} · إفصاحات {len(anns)} · عقود {len(cnt['عقد'])} "
                  f"({total/1e6:,.0f} مليون {share}) · استحواذ {len(cnt['استحواذ'])} · سلبي {len(cnt['سلبي'])}"
                  f" · قيمتُنا÷الهدف {dev} · السعر÷الهدف {pdev}" + (f" · {neg}" if neg else ""))


asyncio.run(main())
