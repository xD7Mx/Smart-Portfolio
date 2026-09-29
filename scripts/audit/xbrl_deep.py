"""حصادٌ عميقٌ لمرّةٍ واحدة (D547): كلُّ ملفّات XBRL في «تداول» لكلّ شركة (حتى 30) لا
أحدثُ ثمانية — فيبلغ التاريخُ 2021 (أقصى ما يتيحه «تداول»: خمسُ سنواتٍ من الإيداعات).
الفتراتُ تُدمج بتاريخها (_merge_old) فلا يمحوها الحصادُ الليليُّ الأقصر.

يعمل في الخلفية داخلَ الحاوية ويكتب تقدّمَه في /tmp/xbrl_deep.log:
    docker exec sp_backend python /app/scripts/audit/xbrl_deep.py
"""
import os
import subprocess
import sys

if os.environ.get("XBRL_DEEP_CHILD") != "1":
    env = {**os.environ, "XBRL_DEEP_CHILD": "1"}
    with open("/tmp/xbrl_deep.log", "w") as log:
        subprocess.Popen([sys.executable, __file__], env=env, stdout=log, stderr=subprocess.STDOUT,
                         start_new_session=True)
    print("بدأ الحصادُ العميق في الخلفية — التقدّمُ في /tmp/xbrl_deep.log")
    sys.exit(0)

import asyncio

sys.path.insert(0, "/app")


async def main():
    from app.services import tadawul_xbrl as X
    from app.services.market_screener import get_cached_screener
    from app.services import lastgood
    syms = [str(r.get("symbol")) for r in get_cached_screener() or [] if r.get("symbol")]
    rep = await X.refresh(syms, conc=4, max_files=30)
    lastgood.flush() if hasattr(lastgood, "flush") else None
    first = {}
    for s in syms:
        an = X.for_symbol(s, "annual")
        y = str(an[0].get("as_of"))[:4] if an else "none"
        first[y] = first.get(y, 0) + 1
    print("DONE", rep, "· أوّلُ سنةٍ سنوية:", dict(sorted(first.items())), flush=True)


asyncio.run(main())
