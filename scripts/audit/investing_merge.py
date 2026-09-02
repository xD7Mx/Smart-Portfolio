"""ترتيبُ المصادر: ياهو المزوّد، والمستورَدُ يملأ الفراغَ — حارسُ D150.

القاعدةُ التي نصّ عليها المالك: «ياهو هو المزوّد، وإنفستنغ مكمِّلٌ عليه».
فإن قصّر استيرادٌ أو غاب ملفٌّ، يعمل التطبيقُ كما هو اليوم بلا انقطاع؛
وإن وُجد، يملأ ما تركه ياهو فارغاً **ولا يستبدل رقماً منه أبداً**.

وهذا الحارسُ سلوكيّ: يبني حالاتٍ ويقيس المخرَج.

    python scripts/audit/investing_merge.py
"""

from __future__ import annotations

import json
import os
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
for _p in ("/app", os.path.join(_ROOT, "backend"), _ROOT, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def main() -> int:
    T: list[tuple[str, bool, str]] = []

    def t(n, ok, d=""):
        T.append((n, bool(ok), d))

    with tempfile.TemporaryDirectory() as state:
        os.environ["SP_STATE_DIR"] = state
        from app.services import investing_store
        from app.services.market_data import _merge_supplement, _investing_rows

        # ١ — بلا ملفّ: لا شيء، ولا سقوط
        investing_store.reload()
        base = [{"year": 2025, "revenue": 100.0, "equity": None}]
        _merge_supplement(base, _investing_rows("2222.SR"))
        t("١ بلا ملفٍّ لا أثرَ ولا سقوط",
          base == [{"year": 2025, "revenue": 100.0, "equity": None}],
          "التطبيقُ يعمل كما هو اليوم")

        # يُكتب ملفٌّ فيه سنةٌ زائدة وقيمٌ تخالف ياهو عمداً
        with open(investing_store.path(), "w", encoding="utf-8") as fh:
            json.dump({"companies": {"2222": [
                {"year": 2024, "revenue": 90.0, "equity": 55.0,
                 "operating_cash_flow": 40.0},
                {"year": 2025, "revenue": 999.0, "equity": 60.0},
            ]}}, fh)
        investing_store.reload()

        # ٢ — رقمُ ياهو لا يُستبدَل
        y = [{"year": 2025, "revenue": 100.0, "equity": None}]
        _merge_supplement(y, _investing_rows("2222"))
        row25 = [r for r in y if r["year"] == 2025][0]
        t("٢ رقمُ ياهو لا يُستبدَل", row25["revenue"] == 100.0,
          f"ياهو 100 · المستورَد 999 · الباقي {row25['revenue']}")

        # ٣ — الفراغُ يمتلئ
        t("٣ الفراغُ يمتلئ من المستورَد", row25["equity"] == 60.0,
          f"كانت None → {row25['equity']}")

        # ٤ — سنةٌ غائبةٌ تُضاف
        years = sorted(r["year"] for r in y)
        t("٤ سنةٌ لا يملكها ياهو تُضاف", years == [2024, 2025], f"{years}")

        # ٥ — الرمزُ بصيغتيه
        a, b = _investing_rows("2222"), _investing_rows("2222.SR")
        t("٥ الرمزُ بصيغتيه سواء", a == b and len(a) == 2,
          f"«2222» {len(a)} · «2222.SR» {len(b)}")

        # ٦ — ملفٌّ تالفٌ لا يُسقط شيئاً
        with open(investing_store.path(), "w", encoding="utf-8") as fh:
            fh.write("{{ تالف")
        investing_store.reload()
        t("٦ ملفٌّ تالفٌ لا يُسقط التطبيق",
          _investing_rows("2222") == [], "يُقرأ فراغاً")

    print("═" * 60)
    print("  ترتيبُ المصادر — ياهو المزوّد والمستورَدُ مكمِّل")
    print("═" * 60)
    for n, ok, d in T:
        print(f"  {'PASS' if ok else 'FAIL'}  {n:34} {d}")
    bad = [n for n, ok, _ in T if not ok]
    print("═" * 60)
    print("  ✔ يملأ الفراغَ ولا يستبدل رقماً." if not bad
          else f"  ✖ أخفق {len(bad)}")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
