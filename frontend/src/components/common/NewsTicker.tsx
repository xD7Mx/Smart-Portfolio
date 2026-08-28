import React, { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Radio } from "lucide-react";
import { marketApi } from "../../services/api";
import { useAppStore } from "../../store/appStore";

// Constant readable speed regardless of how many headlines are loaded —
// previously the animation had a fixed 60s duration no matter the content
// width, so more headlines meant a visually faster (unreadable) scroll.
const PX_PER_SECOND = 70;

/**
 * Top news ticker — a continuously scrolling strip of the latest real
 * headlines, like professional finance portals. Pauses on hover; each
 * headline links to its article. RTL-aware and mobile-friendly.
 */
// Normalizes the four content sources (market news, market calendar,
// portfolio news, portfolio calendar) into one shape the ticker can render,
// tagging each with a `kind` label so the mix stays readable at a glance.
function normalize(items: any[], kind: string, label: string) {
  return (items || []).map((n: any) => ({
    id: `${kind}-${n.id ?? n.headline ?? n.title}`,
    headline: n.headline ?? n.title ?? "",
    source: n.source || n.company_name || n.symbol || label,
    url: n.url || null,
    kind,
  })).filter(n => n.headline);
}

export default function NewsTicker() {
  // The ticker is a pure reflection of the Market tab's news feed (the whole
  // market, from the approved sources) — it deliberately does NOT pull from
  // the calendar/المفكرة. One source only.
  const { language } = useAppStore();
  /* حالة الطلب لا عدد العناصر: الشريط كان يعرض «جارٍ التحميل» كلّما كانت
     القائمة فارغة — سواءٌ لم يصل الردّ بعد، أم وصل فارغاً، أم فشل. فيبقى
     يدّعي التحميل إلى الأبد في أعلى **كل** صفحة، ولا سبيل للمستخدم أن يعرف
     أن لا أخبار أو أن الجلب أخفق. */
  const { data: marketNews = [], isPending, isError, refetch } = useQuery({
    queryKey: ["market-news", language],
    queryFn: () => marketApi.news(language).then(r => (Array.isArray(r.data.data) ? r.data.data : [])),
    refetchInterval: 5 * 60 * 1000,
  });

  // Sources-only, exactly like the Market tab: keep items from an approved
  // outlet (trusted) or tied to a company — never generic aggregator noise.
  const news = React.useMemo(
    () => normalize(marketNews.filter((n: any) => n?.trusted || n?.company), "news", "أخبار السوق"),
    [marketNews]
  );

  const trackRef = useRef<HTMLDivElement>(null);
  const viewportRef = useRef<HTMLDivElement>(null);
  const [duration, setDuration] = useState(60);
  const seenRef = useRef<Set<string> | null>(null);
  const [freshKeys, setFreshKeys] = useState<Set<string>>(new Set());

  // Keep the last non-empty list around so a brief refetch gap (or a
  // temporarily empty response) never blanks the strip — it keeps
  // spinning continuously instead of disappearing and popping back in.
  const lastGoodRef = useRef<any[]>([]);
  if (Array.isArray(news) && news.length > 0) lastGoodRef.current = news;
  // If the combined real content is sparse (e.g. only a couple of items),
  // one pass can end up narrower than the viewport — the two-pass marquee
  // trick then leaves a visible gap before it loops, which reads as the
  // ticker "starting far" from the label instead of flowing right under it.
  // Repeating the base list guarantees enough width regardless of how much
  // real content currently exists.
  const base = lastGoodRef.current;
  const padded = base.length > 0 && base.length < 8
    ? Array.from({ length: Math.ceil(8 / base.length) * base.length }, (_, i) => base[i % base.length])
    : base;
  const items = padded.slice(0, 40);
  const keyOf = (n: any) => String(n.id ?? n.headline);

  useEffect(() => {
    const el = trackRef.current;
    if (!el) return;
    // The track renders the item list twice back-to-back (for the seamless
    // loop), so half its scrollWidth is the actual one-pass content width —
    // that's the full loop distance now that it starts already in place.
    const halfWidth = el.scrollWidth / 2;
    if (halfWidth > 0) setDuration(Math.max(20, halfWidth / PX_PER_SECOND));
  }, [items.length, JSON.stringify(items.map((n: any) => n.headline))]);

  useEffect(() => {
    if (!items.length) return;
    if (seenRef.current === null) {
      // First load: nothing is "new" yet, just record what we've seen.
      seenRef.current = new Set(items.map(keyOf));
      return;
    }
    const fresh = new Set(items.map(keyOf).filter(k => !seenRef.current!.has(k)));
    items.forEach(n => seenRef.current!.add(keyOf(n)));
    if (fresh.size > 0) setFreshKeys(fresh);
  }, [items.length, JSON.stringify(items.map((n: any) => n.headline))]);

  // Resume reading where you left off: after opening a headline (new tab)
  // and coming back, jump straight back to the beginning was disorienting
  // for reading — a negative animation-delay starts the marquee already
  // playing as if it had been running since that headline passed, so it
  // opens right where you clicked instead of restarting from item 1.
  /* استئناف الشريط بعد العودة من الخبر: الخبر يُفتح في لسانٍ جديد فتبقى
     الصفحة حيّة والشريط موقوفاً عند موضعه. العودة تُستشعر بـ`visibilitychange`
     أو باستعادة التركيز. ولمسةٌ في أي مكانٍ آخر تُستأنف أيضاً — صمّامُ أمان
     كي لا يبقى الشريط واقفاً إن لم يُفتح الرابط أصلاً. */
  /* الاستئناف التلقائيّ — كشريط السوق: الإيقاف لقراءة سطرٍ عابر لا
     لتجميد الشريط إلى الأبد. */
  const resumeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => () => { if (resumeTimer.current) clearTimeout(resumeTimer.current); }, []);
  const pausedRef = useRef(false);
  useEffect(() => {
    const resume = () => {
      if (!pausedRef.current || document.visibilityState !== "visible") return;
      const track = trackRef.current;
      if (track) track.style.animationPlayState = "";
      pausedRef.current = false;
    };
    document.addEventListener("visibilitychange", resume);
    window.addEventListener("focus", resume);
    window.addEventListener("pointerdown", resume);
    return () => {
      document.removeEventListener("visibilitychange", resume);
      window.removeEventListener("focus", resume);
      window.removeEventListener("pointerdown", resume);
    };
  }, []);

  const resumedRef = useRef(false);
  useEffect(() => {
    const track = trackRef.current;
    if (!track || !items.length || resumedRef.current) return;
    const lastId = localStorage.getItem("newsTicker:lastId");
    if (!lastId) { resumedRef.current = true; return; }
    const target = track.querySelector<HTMLElement>(`[data-nid="${CSS.escape(lastId)}"]`);
    if (!target) { resumedRef.current = true; return; }
    const trackRect = track.getBoundingClientRect();
    const itemRect = target.getBoundingClientRect();
    const isRtl = document.documentElement.dir === "rtl";
    const distance = isRtl ? (trackRect.right - itemRect.right) : (itemRect.left - trackRect.left);
    if (distance > 0) track.style.animationDelay = `-${distance / PX_PER_SECOND}s`;
    resumedRef.current = true;
  }, [items.length, duration]);

  // Rendered as plain arrays (not a locally-defined "Row" component, which
  // React would treat as a brand-new component type on every re-render and
  // remount) — each pass gets its own key prefix so the two back-to-back
  // copies never collide on the same key, which previously confused React's
  // reconciliation on every background refetch and could silently corrupt
  // the DOM until the strip went blank.
  const renderPass = (pass: "a" | "b") =>
    items.map((n: any, i: number) => {
      const isNew = freshKeys.has(keyOf(n));
      const body = (
        <span className="ticker-item">
          {/* The red "breaking" blinker REPLACES the regular cyan dot — two
              dots side by side read as visual noise, not an urgency signal. */}
          {isNew ? <span className="ticker-new-dot" /> : <span className="ticker-dot" />}
          {n.source && <span className="ticker-src">{n.source}</span>}
          <span className="ticker-txt">{n.headline}</span>
        </span>
      );
      const key = `${pass}-${keyOf(n)}-${i}`;
      const nid = `${pass}-${keyOf(n)}`;
      /* الضغط يوقف الشريط في مكانه بالضبط. الإيقاف نفسه يحفظ الموضع — لا
         حساب ولا تخمين — فحين تعود من الخبر يُستأنف من حيث وقف تماماً. */
      const onClick = () => {
        localStorage.setItem("newsTicker:lastId", `a-${keyOf(n)}`);
        const track = trackRef.current;
        if (track) {
          track.style.animationPlayState = "paused"; pausedRef.current = true;
          if (resumeTimer.current) clearTimeout(resumeTimer.current);
          resumeTimer.current = setTimeout(() => {
            const el = trackRef.current;
            if (el) el.style.animationPlayState = "";
            pausedRef.current = false;
          }, 6000);
        }
      };
      return n.url
        ? <a key={key} data-nid={nid} href={n.url} target="_blank" rel="noopener noreferrer" className="ticker-link" onClick={onClick}>{body}</a>
        : <span key={key} data-nid={nid} className="ticker-link">{body}</span>;
    });

  return (
    <div className="news-ticker">
      <div className="news-ticker-label">
        <Radio size={13} />
        <span>الأخبار</span>
      </div>
      <div className="news-ticker-viewport" ref={viewportRef}>
        {items.length ? (
          <div
            className="news-ticker-track"
            ref={trackRef}
            style={{ animationDuration: `${duration}s` }}
          >
            {renderPass("a")}
            {renderPass("b")}
          </div>
        ) : isPending ? (
          <div className="ticker-loading">
            <span>جارٍ التحميل</span>
            <span className="ldots"><i></i><i></i><i></i></span>
          </div>
        ) : isError ? (
          <div className="ticker-loading">
            <span>تعذّر جلب الأخبار</span>
            <button onClick={() => refetch()} className="ticker-retry">إعادة المحاولة</button>
          </div>
        ) : (
          <div className="ticker-loading"><span>لا أخبار جديدة</span></div>
        )}
      </div>
    </div>
  );
}
