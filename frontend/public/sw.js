/* ══════════════════════════════════════════════════════════════════════
   Service Worker — «المحفظة الذكية»

   قاعدة حاكمة واحدة تحكم كل سطر هنا:
   **لا يُخزَّن أي طلب بيانات مالية إطلاقاً.**
   كاش البيانات المالية خطر حقيقي: يعرض سعراً/رصيداً قديماً كأنه حيّ، وهذا
   أسوأ من عدم العرض. لذلك كل ما تحت /api/ يمرّ للشبكة مباشرةً بلا وسيط،
   ولا يُكتب في أي كاش تحت أي ظرف.

   ما يُخزَّن: أصول التطبيق فقط (JS/CSS/خطوط/أيقونات) — وهي مُبصَّمة بالهاش
   من Vite فلا تتعارض نسخة بأخرى.

   الاستراتيجيات:
     • الأصول المُبصَّمة (assets/*)  → Cache-First (لا تتغيّر أبداً لنفس الاسم)
     • مستند HTML                    → Network-First مع رجوع للكاش عند الانقطاع
     • /api/*                        → شبكة فقط، بلا كاش، بلا اعتراض تخزيني
   ══════════════════════════════════════════════════════════════════════ */

const VERSION = "sp-v1";
const SHELL_CACHE = `${VERSION}-shell`;
const ASSET_CACHE = `${VERSION}-assets`;

// الحدّ الأدنى الذي يجعل التطبيق يُقلع بلا شبكة.
const SHELL = ["/", "/index.html", "/manifest.webmanifest"];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(SHELL_CACHE)
      .then((c) => c.addAll(SHELL).catch(() => undefined))
      // لا ننتظر إغلاق كل التبويبات: التحديث يُفعَّل فور قبول المستخدم.
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys.filter((k) => !k.startsWith(VERSION)).map((k) => caches.delete(k))
      ))
      .then(() => self.clients.claim())
  );
});

/** هل هذا طلب بيانات؟ (لا يُخزَّن أبداً) */
function isData(url) {
  return url.pathname.startsWith("/api/");
}

/** هل هذا أصل مُبصَّم بالهاش من البناء؟ */
function isHashedAsset(url) {
  return url.pathname.startsWith("/assets/")
    || /\.(woff2?|ttf|png|svg|jpg|jpeg|webp|ico)$/i.test(url.pathname);
}

self.addEventListener("fetch", (event) => {
  const req = event.request;

  // لا نتدخّل إطلاقاً في: غير GET · نطاقات أخرى · أي طلب بيانات.
  if (req.method !== "GET") return;
  let url;
  try { url = new URL(req.url); } catch { return; }
  if (url.origin !== self.location.origin) return;
  if (isData(url)) return;                    // ← البيانات المالية: شبكة فقط

  // الأصول المُبصَّمة: من الكاش فوراً، وتُخزَّن عند أول جلب.
  if (isHashedAsset(url)) {
    event.respondWith(
      caches.match(req).then((hit) => hit || fetch(req).then((res) => {
        if (res && res.status === 200 && res.type === "basic") {
          const copy = res.clone();
          caches.open(ASSET_CACHE).then((c) => c.put(req, copy)).catch(() => {});
        }
        return res;
      }).catch(() => hit))
    );
    return;
  }

  // التنقّل/المستند: الشبكة أولاً (ليصل أحدث إصدار)، والكاش شبكة أمان
  // عند الانقطاع فقط — فلا يعلق المستخدم على شاشة خطأ المتصفح.
  if (req.mode === "navigate" || req.headers.get("accept")?.includes("text/html")) {
    event.respondWith(
      fetch(req).then((res) => {
        const copy = res.clone();
        caches.open(SHELL_CACHE).then((c) => c.put("/index.html", copy)).catch(() => {});
        return res;
      }).catch(() => caches.match("/index.html").then((r) => r || Response.error()))
    );
  }
});

// تفعيل فوري بناءً على طلب الواجهة (بعد موافقة المستخدم على التحديث).
self.addEventListener("message", (e) => {
  if (e.data === "SKIP_WAITING") self.skipWaiting();
});
