import React from "react";
import CompanyLogo from "../common/CompanyLogo";

/* ══ «نجوم تاسي 20» ══ (D522 · على نمط InvestingPro من صور المالك)
   بطاقةُ الأداء أوّلاً (الإجماليّ · المتفوّق · تاسي)، ثمّ منحنى السلّة مقابلَ
   تاسي من السجلّ الحيّ، ثمّ الأعضاءُ بمكرّر ربحيتهم. وما لا مصدرَ له «غير متوفّر». */

const pct = (v: any) => (typeof v === "number" ? `${v > 0.05 ? "+" : ""}${Math.abs(v) < 0.05 ? "0.0" : v.toFixed(1)}%` : "—");
const tone = (v: any) => (typeof v === "number" && Math.abs(v) >= 0.05 ? (v > 0 ? "text-[var(--pos-ink)]" : "text-[var(--neg-ink)]") : "text-[var(--ink)]");

export function Curve({ track: raw }: { track: { d: string; s: number; t: number }[] }) {
  /* ‏D542: يومُ البداية نقطةٌ واحدة — يُرسم خطُّ الأساس 100 للمؤشّرين لا فراغ. */
  const base = raw && raw.length ? raw : [{ d: "", s: 100, t: 100 }];
  const track = base.length === 1 ? [base[0], { ...base[0] }] : base;
  const W = 600, H = 140, P = 6;
  const all = track.flatMap(p => [p.s, p.t]);
  let lo = Math.min(...all), hi = Math.max(...all);
  if (hi - lo < 1e-9) { lo -= 1; hi += 1; }            // خطٌّ مستوٍ يُوسَّط لا يلتصق بالقاع
  const span = hi - lo;
  const x = (i: number) => P + (i / (track.length - 1)) * (W - 2 * P);
  const y = (v: number) => H - P - ((v - lo) / span) * (H - 2 * P);
  const path = (k: "s" | "t") => track.map((p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(p[k]).toFixed(1)}`).join("");
  const area = path("s") + `L${x(track.length - 1)},${H - P}L${x(0)},${H - P}Z`;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-[140px]" preserveAspectRatio="none" role="img"
      aria-label="أداءُ نجوم تاسي مقابلَ تاسي">
      <path d={area} style={{ fill: "color-mix(in srgb, var(--brand) 14%, transparent)" }} />
      <path d={path("t")} fill="none" style={{ stroke: "var(--ink-muted)" }} strokeWidth={1.5} vectorEffect="non-scaling-stroke" />
      <path d={path("s")} fill="none" style={{ stroke: "var(--brand-ink)" }} strokeWidth={2} vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

export default function TasiStarsPanel({ data, loading, onPick }: { data: any; loading: boolean; onPick: (s: string) => void }) {
  if (loading) return <div className="card h-[320px] skeleton" />;
  if (!data?.members?.length) {
    return <div className="card py-10 text-center text-sm text-[var(--ink-muted)]">غير متوفّر</div>;
  }
  const s = data.summary || {};
  const stat = (label: string, v: any) => (
    <div className="rounded-xl border border-[var(--hairline)] px-3 py-2 min-w-0">
      <div className="text-[11px] text-[var(--ink-muted)] truncate">{label}</div>
      <div className={"text-lg font-bold tabular-nums " + tone(v)} dir="ltr">{pct(v)}</div>
    </div>
  );
  const info = (label: string, v: string) => (
    <div className="rounded-xl border border-[var(--hairline)] px-3 py-2 min-w-0">
      <div className="text-[11px] text-[var(--ink-muted)] truncate">{label}</div>
      <div className="text-[13px] font-semibold text-[var(--ink)] truncate">{v}</div>
    </div>
  );
  return (
    <div className="card space-y-3">
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-base font-bold text-[var(--ink)]">نجوم تاسي</h2>
        <span className="tag-b" dir="ltr">TASI20</span>
      </div>
      <div className="grid grid-cols-3 gap-2">
        {stat("العائد الإجماليّ", s.total)}
        {stat("الأداءُ المتفوّق", s.excess)}
        {stat("تاسي", s.tasi_total)}
      </div>
      <div>
        <div className="flex items-center gap-3 text-[11px] text-[var(--ink-muted)]">
          <span className="flex items-center gap-1"><span className="w-2.5 h-0.5 inline-block" style={{ background: "var(--brand-ink)" }} />نجوم تاسي</span>
          <span className="flex items-center gap-1"><span className="w-2.5 h-0.5 inline-block" style={{ background: "var(--ink-muted)" }} />تاسي</span>
        </div>
        <Curve track={data.track || []} />
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        {info("بدايةُ السجلّ", data.inception || data.since)}
        {info("إعادةُ التوازن", data.rebalance || "شهرياً")}
        {info("التركيز", data.universe || "شركاتٌ كبيرة")}
        {info("الأوزان", data.weighting || "متساوية")}
      </div>
      <div className="divide-y divide-[var(--hairline)]">
        <div className="grid grid-cols-[1fr_auto_auto] gap-3 py-1.5 text-[11px] text-[var(--ink-muted)]">
          <span>الاسم</span><span className="w-14 text-center">مكرّر الربحية</span><span className="w-14 text-center">إلى العادل</span>
        </div>
        {data.members.map((m: any) => (
          <button key={m.symbol} type="button" onClick={() => onPick(m.symbol)}
            className="w-full grid grid-cols-[1fr_auto_auto] items-center gap-3 py-2 min-h-[32px] text-start hover:bg-[var(--field)]">
            <span className="flex items-center gap-2 min-w-0">
              <CompanyLogo symbol={m.symbol} size={24} />
              <span className="min-w-0">
                <span className="block text-[13px] font-semibold text-[var(--ink)] truncate">{m.name}</span>
                <span className="block text-[11px] text-[var(--ink-muted)] tabular-nums" dir="ltr">{m.symbol}</span>
              </span>
            </span>
            <span className="w-14 text-center text-[13px] font-bold tabular-nums text-[var(--ink)]" dir="ltr">
              {typeof m.pe === "number" ? `${m.pe.toFixed(1)}x` : "—"}</span>
            <span className={"w-14 text-center text-[13px] font-bold tabular-nums " + tone(m.upside)} dir="ltr">{pct(m.upside)}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
