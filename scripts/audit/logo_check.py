#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# شعاراتُ الشركات — **مسبارُ قياسٍ لا إصلاح**.
#
# قال المالك: «صور الشركات لا تظهر» في فرز السوق. والرموزُ التي رآها فارغةً
# (‏8020 · 8030 · 8040) **لها روابطُ في الخريطة** — فالسببُ ليس غياباً،
# وأمامنا احتمالان لا يُرجَّح بينهما بالنظر:
#   ١· الرابطُ لا يُحمَّل (‏404 · حجبٌ · مهلة) — فالفشلُ صامتٌ ويظهر فراغ
#   ٢· يُحمَّل والصورةُ **فاتحةٌ أو شبه شفّافة** — فتُرى بيضاء على الأرضية
#
# والعلاجان مختلفان تماماً: الأوّلُ يُصلح بالمصدر، والثاني بخلفيةٍ للشعار.
# فيُقاس: يُجلب كلُّ رابط، ويُقرأ حجمُه وحالتُه، وتُحسب نسبةُ البكسل الفاتح
# والشفّاف فيه.
#
#   docker exec sp_backend python /app/scripts/audit/logo_check.py
#   docker exec sp_backend python /app/scripts/audit/logo_check.py 8020 8030 8040
#
# لا يكتب شيئاً ولا يغيّر رابطاً — يقرأ ويطبع.
# ─────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import re
import sys
import pathlib
import urllib.request

ROOT = pathlib.Path("/app") if pathlib.Path("/app/frontend").exists() else \
       pathlib.Path(__file__).resolve().parents[2]
MAP = ROOT / "frontend" / "src" / "data" / "tradingviewLogos.ts"
UA = {"User-Agent": "Mozilla/5.0 (logo-probe)"}
SAMPLE = ["8020", "8030", "8040", "8012", "8210", "8010", "8170", "8250"]


def links() -> dict[str, str]:
    if not MAP.exists():
        print(f"… لم يُعثر على خريطة الشعارات: {MAP}")
        return {}
    txt = MAP.read_text(encoding="utf-8")
    return dict(re.findall(r'"(\d{4})"\s*:\s*"([^"]+)"', txt))


def analyse(raw: bytes) -> str:
    """نسبةُ الفاتح والشفّاف — بلا اعتماديةٍ خارجية إن غابت الوسادة."""
    try:
        from PIL import Image           # type: ignore
        import io
    except Exception:                                             # noqa: BLE001
        return "تعذّر التحليل (Pillow غير مثبَّت) — الحجمُ وحدَه دليل"
    try:
        im = Image.open(io.BytesIO(raw)).convert("RGBA")
        im.thumbnail((48, 48))
        px = list(im.getdata())
        n = len(px) or 1
        clear = sum(1 for r, g, b, a in px if a < 32)
        light = sum(1 for r, g, b, a in px if a >= 32 and (r + g + b) / 3 > 220)
        ink = n - clear - light
        return (f"شفّاف {clear * 100 // n}٪ · فاتحٌ جداً {light * 100 // n}٪ "
                f"· حبرٌ مرئيّ {ink * 100 // n}٪"
                + ("  ⚠ لا حبرَ يُرى على أرضيةٍ فاتحة" if ink * 100 // n < 8 else ""))
    except Exception as e:                                        # noqa: BLE001
        return f"تعذّر التحليل ({type(e).__name__})"


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    m = links()
    if not m:
        return 2
    syms = args or SAMPLE
    print(f"خريطةُ الشعارات: {len(m)} رابطاً · يُقاس {len(syms)}")
    print("─" * 74)
    ok = broken = pale = 0
    for s in syms:
        url = m.get(s)
        if not url:
            print(f"■ {s}: لا رابطَ في الخريطة")
            broken += 1
            continue
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=20) as r:
                raw = r.read()
                code = r.status
        except Exception as e:                                    # noqa: BLE001
            print(f"■ {s}: ✖ {type(e).__name__} — {url}")
            broken += 1
            continue
        note = analyse(raw)
        if "لا حبرَ يُرى" in note:
            pale += 1
        else:
            ok += 1
        print(f"■ {s}: ‎{code} · {len(raw):,} بايت · {note}")
    print("─" * 74)
    print(f"سليمة {ok} · متعذّرة {broken} · فاتحةٌ لا تُرى {pale}")
    print("إن كانت متعذّرةً فالعلاجُ في المصدر، وإن كانت فاتحةً فالعلاجُ")
    print("خلفيةٌ للشعار — ولا يُبنى علاجٌ قبل أن يُعرف أيُّهما.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
