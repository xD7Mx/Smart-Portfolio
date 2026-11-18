/* ══ السعرُ الحيُّ وحالةُ السوق كتريدنق فيو ══ (‏D761 · بأمر المالك 2026-11-17)
   «علامةٌ بجانب اسم الشركة — رمزٌ للسوق مثل تريدينق فيو بالضبط: مفتوح، قبل الماركت، بعد الماركت… مغلق، عطلة — وأريد الأرقام تتحرّك،
   أريد حيوية». فالشارةُ بأيقونة تريدنق فيو ولونِها (مفتوح: نقطةٌ خضراءُ تنبض · قبل الافتتاح: شمس · بعد الإغلاق: قمر · مغلق: نقطةٌ رمادية ·
   عطلة: تقويم)، والسعرُ يُجلب كلَّ خمس ثوانٍ والسوقُ في جلسة (كلَّ دقيقةٍ وهو مغلق) ويومض بلون اتجاهه، وما قبل الافتتاح وبعده سطرٌ تحته. */
import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Sun, Moon, Star, Timer } from "lucide-react";
import { marketApi } from "../../services/api";

export type Session = { market: "us" | "sa"; state: "pre" | "open" | "post" | "closed" | "holiday" | "auction" | "preopen"; label: string;
  detail: string; next: string | null; holiday?: string; source?: string };
export type Live = { symbol: string; price: number | null; change?: number | null; change_pct?: number | null; prev_close?: number | null;
  time?: string | null; delayed?: number; source?: string | null; session: Session; earnings?: string | null;
  ext?: { kind: "pre" | "post"; price: number; change: number | null; change_pct: number | null } | null };

const ACTIVE = new Set(["pre", "open", "post", "auction", "preopen"]);
const hidden = () => typeof document !== "undefined" && document.visibilityState === "hidden";

export function useLive(symbol: string | null | undefined) {
  return useQuery<Live | null>({
    queryKey: ["live", symbol],
    queryFn: () => marketApi.live(symbol as string).then(r => r.data?.data ?? null),
    enabled: !!symbol, retry: 0, staleTime: 3_000,
    refetchInterval: q => (hidden() ? false : ACTIVE.has((q.state.data as Live | null)?.session?.state || "") ? 5_000 : 60_000),
    refetchOnWindowFocus: true,
  });
}

const fmt = (v: number) => v.toLocaleString("en-US", { minimumFractionDigits: v >= 1 ? 2 : 4, maximumFractionDigits: v >= 1 ? 2 : 4 });
const sgn = (v: number, d = 2) => (v >= 0 ? "+" : "") + v.toFixed(d);

/* ‏D762: حالةُ السوقين بنداءٍ واحدٍ لقوائم المراقبة — لا نداءٌ لكلّ سطر */
export function useSessions() {
  return useQuery<{ us: Session; sa: Session } | null>({
    queryKey: ["sessions"], queryFn: () => marketApi.sessions().then(r => r.data?.data ?? null),
    staleTime: 25_000, refetchInterval: () => (hidden() ? false : 60_000), retry: 0,
  });
}

/* أيقونةُ الحالة وحدها بجانب اسم الشركة في القائمة — كتريدنق فيو: نقطةٌ خضراء (مفتوح) · شمس (قبل الافتتاح) · قمرٌ أزرق (بعد الإغلاق) ·
   نقطةٌ رمادية (مغلق) · نجمةٌ رمادية (عطلة) — والعملاتُ المشفّرةُ تتداول على مدار الساعة */
export function SessionDot({ s, always }: { s?: Session | null; always?: boolean }) {
  if (always) return <span className="lq-sdot lq-open" title="يتداول على مدار الساعة" aria-label="يتداول على مدار الساعة" data-role="lq-dot" data-state="open"><span className="lq-dot" /></span>;
  if (!s) return null;
  const st = s.state;
  const title = `${s.holiday ? `عطلة: ${s.holiday}` : s.label} · ${s.detail}`;
  return (
    <span className={`lq-sdot lq-${st}`} title={title} aria-label={title} data-role="lq-dot" data-state={st}>
      {st === "pre" ? <Sun size={11} strokeWidth={2.4} /> : st === "post" ? <Moon size={10} strokeWidth={2.4} fill="currentColor" />
        : st === "holiday" ? <Star size={10} strokeWidth={2.2} fill="currentColor" /> : st === "auction" || st === "preopen" ? <Timer size={10} strokeWidth={2.4} />
        : <span className="lq-dot" />}
    </span>
  );
}

export function SessionBadge({ s, compact = false }: { s: Session; compact?: boolean }) {
  const st = s.state;
  const icon = st === "pre" ? <Sun size={13} strokeWidth={2.4} /> : st === "post" ? <Moon size={12} strokeWidth={2.4} />
    : st === "holiday" ? <Star size={12} strokeWidth={2.2} fill="currentColor" /> : st === "auction" || st === "preopen" ? <Timer size={12} strokeWidth={2.4} />
    : <span className="lq-dot" />;
  const title = `${s.holiday ? `عطلة: ${s.holiday}` : s.label} · ${s.detail}`;
  return (
    <span className={`lq-badge lq-${st}`} title={title} aria-label={title} data-role="lq-session" data-state={st}>
      {icon}{!compact && <span className="lq-blabel">{s.holiday || s.label}</span>}
    </span>
  );
}

export default function LiveQuote({ symbol, live }: { symbol: string; live: Live | null | undefined }) {
  const [flash, setFlash] = useState<"" | "up" | "dn">("");
  const prev = useRef<{ sym: string; px: number | null }>({ sym: symbol, px: null });
  const px = live?.price ?? null;
  useEffect(() => {
    const p = prev.current;
    if (p.sym === symbol && p.px != null && px != null && px !== p.px) {
      setFlash(px > p.px ? "up" : "dn");
      const t = window.setTimeout(() => setFlash(""), 700);
      prev.current = { sym: symbol, px };
      return () => window.clearTimeout(t);
    }
    prev.current = { sym: symbol, px };
  }, [px, symbol]);
  if (!live?.session) return null;
  const ch = live.change_pct;
  const ext = live.ext;
  return (
    <span className="lq" data-role="lq">
      <SessionBadge s={live.session} />
      {px != null && (
        <span className="lq-px-wrap">
          <span className={"lq-px" + (flash ? ` lq-flash-${flash}` : "")} dir="ltr" data-role="lq-price">{fmt(px)}</span>
          {ch != null && (
            <span className={"lq-ch " + (ch >= 0 ? "pos" : "neg")} dir="ltr" data-role="lq-change">
              {live.change != null ? `${sgn(live.change)} ` : ""}({sgn(ch)}%)
            </span>
          )}
          {!!live.delayed && <span className="lq-delay" title={`أسعارٌ مؤجّلةٌ ${live.delayed} دقيقة (${live.source})`}>مؤجّل {live.delayed}د</span>}
        </span>
      )}
      {ext && ext.price != null && (
        <span className="lq-ext" data-role="lq-ext" title={ext.kind === "pre" ? "سعرُ ما قبل الافتتاح" : "سعرُ ما بعد الإغلاق"}>
          {ext.kind === "pre" ? <Sun size={11} /> : <Moon size={10} />}
          <span dir="ltr">{fmt(ext.price)}</span>
          {ext.change_pct != null && <span dir="ltr" className={ext.change_pct >= 0 ? "pos" : "neg"}>{sgn(ext.change_pct)}%</span>}
        </span>
      )}
    </span>
  );
}
