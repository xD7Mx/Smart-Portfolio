"""كاشفٌ تشخيصيّ: خطواتُ القارئ البصري لملفٍّ واحد من سدافكو — التنزيلُ إلى القرص، وبدءُ الرفع،
والرفع، ثمّ القراءة — بحالة كلّ خطوةٍ ونصِّها مختصراً (والمفتاحُ محجوب). (D565)

    docker exec sp_backend python /app/scripts/audit/file_upload_diag.py
"""
import asyncio
import os
import sys
import tempfile

sys.path.insert(0, "/app")


async def main():
    import httpx
    from app.core.config import settings
    from app.services.tadawul_pdf import pdf_links
    from app.services.tadawul_http import fetch_to_file
    from app.services.file_reader import pick
    K = settings.AI_API_KEY or ""
    hide = lambda t: (t or "").replace(K, "***")[:400]
    links, why = await pdf_links("2270")
    p = pick(links)
    print("@@LINKS@@", len(links), why, [x["filed"] for x in p])
    if not p:
        return
    fd, tmp = tempfile.mkstemp(suffix=".pdf"); os.close(fd)
    try:
        st, n = await fetch_to_file(p[0]["url"], tmp, referer=p[0]["referer"])
        head = open(tmp, "rb").read(8)
        print("@@DOWNLOAD@@", st, n, head)
        size = os.path.getsize(tmp)
        base = "https://generativelanguage.googleapis.com"
        async with httpx.AsyncClient(timeout=180) as c:
            r = await c.post(f"{base}/upload/v1beta/files?key={K}",
                             headers={"X-Goog-Upload-Protocol": "resumable", "X-Goog-Upload-Command": "start",
                                      "X-Goog-Upload-Header-Content-Length": str(size),
                                      "X-Goog-Upload-Header-Content-Type": "application/pdf",
                                      "Content-Type": "application/json"},
                             json={"file": {"display_name": "sp-diag"}})
            print("@@START@@", r.status_code, "upload-url" if r.headers.get("x-goog-upload-url") else "no-url", hide(r.text))
            up = r.headers.get("x-goog-upload-url")
            if not up:
                return
            data = open(tmp, "rb").read()
            r = await c.post(up, content=data, headers={"Content-Length": str(size), "X-Goog-Upload-Offset": "0",
                                                       "X-Goog-Upload-Command": "upload, finalize"})
            print("@@UPLOAD@@", r.status_code, hide(r.text))
            f = (r.json() or {}).get("file") or {} if r.status_code == 200 else {}
            if f.get("uri"):
                g = await c.post(f"{base}/v1beta/models/{settings.AI_MODEL}:generateContent?key={K}",
                                 json={"contents": [{"parts": [{"file_data": {"mime_type": "application/pdf", "file_uri": f["uri"]}},
                                                               {"text": "ما الفترةُ التي يغطّيها هذا الملفّ؟ سطرٌ واحد."}]}]})
                print("@@GENERATE@@", g.status_code, hide(g.text))
                await c.delete(f"{base}/v1beta/{f['name']}?key={K}")
    finally:
        os.remove(tmp)


asyncio.run(main())
