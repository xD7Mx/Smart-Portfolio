"""‏D704 — يكتب دليلَ «تداول» (صفحتا السوق الرئيسية ونمو باللغتين) في مخزن الحالة كما تفعل المزامنةُ الليلية، ويطبع ما تغيّر.

يكتب مفتاحَ الدليل وحده (‏market:tadawul_directory) — لا يمسّ أرقامَ المالك ولا تقييماً. ويقرؤه الكونُ عند الإقلاع التالي.

    docker exec sp_backend python /app/scripts/audit/tadawul_directory_sync.py
"""
import asyncio
import sys

sys.path.insert(0, "/app")


async def main():
    from app.services.tadawul_sync import sync_directory, directory
    r = await sync_directory()
    print("@@SYNC@@", {k: (v if k not in ("added", "gone") else v[:20]) for k, v in r.items()})
    d = directory()
    for s in ("1325", "2001", "4230", "4030", "4090", "2230"):
        print(f"@@SYM@@ {s} {'الرئيسية' if s in (d.get('main') or {}) else 'نمو' if s in (d.get('nomu') or {}) else '—'} · "
              f"{((d.get('main') or {}).get(s) or (d.get('nomu') or {}).get(s) or {})}")


asyncio.run(main())
