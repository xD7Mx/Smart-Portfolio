"""
Merged read-only market universe (~395 Tadawul symbols) from the site's own
already-injected static sources — never a live DB table, so nothing here
can ever be mistaken for a portfolio holding (the exact class of bug the
directory-ghost-company incident was): company_names_en (219, English
names), company_sectors (219, Arabic sectors), tradingview_logos (389 real
verified logos + Arabic names). Powers the Governance page's "السوق" mode.
"""

from app.data.company_names_en import SYMBOL_TO_NAME_EN
from app.data.company_sectors import SYMBOL_TO_SECTOR_AR
from app.data.tradingview_logos import TRADINGVIEW_LOGOS


def _build() -> dict[str, dict]:
    universe: dict[str, dict] = {}
    for sym, name_en in SYMBOL_TO_NAME_EN.items():
        universe.setdefault(sym, {})["name_en"] = name_en
    for sym, sector in SYMBOL_TO_SECTOR_AR.items():
        universe.setdefault(sym, {})["sector"] = sector
    for sym, entry in TRADINGVIEW_LOGOS.items():
        u = universe.setdefault(sym, {})
        u["name_ar"] = entry["name_ar"]
        u["logo_url"] = entry["logo_url"]
    # ══ الاسمُ من الدليل حين لا يحمله مصدرٌ آخر ══
    # كان الكونُ يقرأ الأسماء من شعارات TradingView وحدها، ومن لا شعارَ له
    # يصير اسمُه **رمزَه**: «9405» اسماً و«9405» قطاعاً معروضاً. وهكذا كانت
    # صناديقُ السوق العشرة موجودةً في الكون منذ البداية — بقطاعها الصحيح —
    # وبلا اسمٍ ولا صورة. فرآها المالك «بلا قيمة ولا صورة»، وظننتُها غائبةً
    # عن الدليل فأضفتُها إليه، والعلّةُ هنا لا هناك.
    # ودليلُ السوق (`saudi_directory`) يحمل الاسم العربيّ لكل رمزٍ فيه،
    # فيُقرأ منه قبل السقوط إلى الرمز نفسه — وهو المصدرُ الذي تقرأ منه بقيةُ
    # الشاشات أصلاً، فلا يبقى اسمٌ في شاشةٍ ورقمٌ في أخرى.
    try:
        from app.data.saudi_directory import SAUDI_DIRECTORY as _DIR
    except Exception:                                             # noqa: BLE001
        _DIR = {}
    for sym, u in universe.items():
        d = _DIR.get(sym) or {}
        if d.get("name"):
            u.setdefault("name_ar", d["name"])
        if d.get("name_en"):
            u.setdefault("name_en", d["name_en"])
    for sym, u in universe.items():
        u.setdefault("name_ar", u.get("name_en") or sym)
        u.setdefault("name_en", u.get("name_ar") or sym)
    return universe


MARKET_UNIVERSE: dict[str, dict] = _build()
