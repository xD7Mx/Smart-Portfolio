import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Star } from "lucide-react";
import { marketApi } from "../services/api";
import CompanyLogo from "../components/common/CompanyLogo";
import StockSheet from "../components/market/StockSheet";
import { Curve } from "../components/market/TasiStarsPanel";

/* ══ نجوم تاسي ══ (بأمر المالك · D536) — صفحةٌ مستقلّةٌ ببطاقات: الأداء · النجوم · المعايير. */

const pct = (v: any) => (typeof v === "number" ? `${v >= 0 ? "+" : ""}${v.toFixed(1)}%` : "غير متوفّر");
const tone = (v: any) => (typeof v === "number" ? (v >= 0 ? "text-[var(--pos-ink)]" : "text-[var(--neg-ink)]") : "text-[var(--ink-muted)]");

const RULES: [string, string][] = [
  ["التفوّق على تاسي", "عائدُ 12 شهراً أعلى من عائد تاسي"],
  ["توقّع 12 شهراً", "السعرُ العادل أعلى من السعر بـ15٪ فأكثر"],
  ["ثقة التقييم", "ليست منخفضة"],
  ["الدرجة المالية", "70 فأكثر"],
  ["الخطوط الحمراء", "لا شيء"],
  ["القوائم المالية", "خلال 9 أشهر"],
  ["الشرعية", "ليست غير متوافقة"],
  ["نطاق السوق", "أكبر 100 شركة بالقيمة السوقية"],
  ["السلّة", "20 شركة بأوزانٍ متساوية"],
  ["إعادة التوازن", "شهرياً"],
];

export default function StarsPage() {
  const [sheet, setSheet] = useState<string | null>(null);
  const { data, isLoading } = useQuery({
    queryKey: ["tasi-stars"], staleTime: 5 * 60_000,
    queryFn: () => marketApi.tasiStars().then(r => r.data?.data || null),
  });
  const s = data?.summary || {};
  const stat = (label: string, v: any) => (
    <div className="rounded-xl border border-[var(--hairline)] px-3 py-2 min-w-0">
      <div className="text-[11px] text-[var(--ink-muted)] truncate">{label}</div>
      <div className={"text-lg font-bold tabular-nums " + tone(v)} dir="ltr" style={{ textAlign: "right" }}>{pct(v)}</div>
    </div>
  );
  const info = (label: string, v: string) => (
    <div className="rounded-xl border border-[var(--hairline)] px-3 py-2 min-w-0">
      <div className="text-[11px] text-[var(--ink-muted)] truncate">{label}</div>
      <div className="text-[13px] font-semibold text-[var(--ink)] truncate">{v}</div>
    </div>
  );
  return (
    <div className="space-y-4 fade-in">
      <div className="flex items-center justify-between gap-2">
        <h1 className="text-2xl font-medium text-[var(--ink)] flex items-center gap-2">
          <Star size={22} className="text-[var(--brand-ink)]" /> نجوم تاسي
        </h1>
        <span className="tag-b" dir="ltr">TASI20</span>
      </div>

      {isLoading ? <div className="card h-64 skeleton" /> : !data?.members?.length ? (
        <div className="card py-10 text-center text-sm text-[var(--ink-muted)]">غير متوفّر</div>
      ) : (
        <>
          <div className="card space-y-3">
            <p className="card-title">الأداء</p>
            <div className="grid grid-cols-3 gap-2">
              {stat("العائد الإجماليّ", s.total)}
              {stat("الأداءُ المتفوّق", s.excess)}
              {stat("تاسي", s.tasi_total)}
            </div>
            <div className="flex items-center gap-3 text-[11px] text-[var(--ink-muted)]">
              <span className="flex items-center gap-1"><span className="w-2.5 h-0.5 inline-block" style={{ background: "var(--brand-ink)" }} />نجوم تاسي</span>
              <span className="flex items-center gap-1"><span className="w-2.5 h-0.5 inline-block" style={{ background: "var(--ink-muted)" }} />تاسي</span>
            </div>
            <Curve track={data.track || []} />
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {info("بدايةُ السجلّ", data.inception || data.since)}
              {info("آخرُ توازن", data.since)}
              {info("إعادةُ التوازن", data.rebalance || "شهرياً")}
              {info("الأوزان", data.weighting || "متساوية")}
            </div>
          </div>

          <div className="card p-0">
            <div className="flex items-center justify-between px-4 pt-4 pb-2">
              <p className="card-title">النجوم</p>
              <span className="text-[12px] text-[var(--ink-muted)] tabular-nums">{data.members.length}</span>
            </div>
            <div className="grid grid-cols-[1fr_auto_auto] gap-3 px-4 py-1.5 text-[11px] text-[var(--ink-muted)] border-b border-[var(--hairline)]">
              <span>الشركة</span><span className="w-14 text-center">مكرّر الربحية</span><span className="w-14 text-center">إلى العادل</span>
            </div>
            {data.members.map((m: any) => (
              <button key={m.symbol} type="button" onClick={() => setSheet(m.symbol)}
                className="w-full grid grid-cols-[1fr_auto_auto] items-center gap-3 px-4 py-2 min-h-[44px] text-start border-b border-[var(--hairline)] last:border-0 hover:bg-[var(--field)]">
                <span className="flex items-center gap-2 min-w-0">
                  <CompanyLogo symbol={m.symbol} size={26} />
                  <span className="min-w-0">
                    <span className="block text-[13px] font-semibold text-[var(--ink)] truncate">{m.name}</span>
                    <span className="block text-[11px] text-[var(--ink-muted)] tabular-nums" dir="ltr" style={{ textAlign: "right" }}>{m.symbol}</span>
                  </span>
                </span>
                <span className="w-14 text-center text-[13px] font-bold tabular-nums text-[var(--ink)]" dir="ltr">
                  {typeof m.pe === "number" ? `${m.pe.toFixed(1)}x` : "—"}</span>
                <span className={"w-14 text-center text-[13px] font-bold tabular-nums " + tone(m.upside)} dir="ltr">{pct(m.upside)}</span>
              </button>
            ))}
          </div>
        </>
      )}

      <div className="card">
        <p className="card-title mb-2">المعايير</p>
        {RULES.map(([k, v]) => (
          <div key={k} className="flex items-center justify-between gap-3 min-h-[36px] border-b border-[var(--hairline)] last:border-0">
            <span className="text-[13px] text-[var(--ink)]">{k}</span>
            <span className="text-[13px] font-semibold text-[var(--ink-muted)] text-end">{v}</span>
          </div>
        ))}
      </div>
      {sheet && <StockSheet symbol={sheet} onClose={() => setSheet(null)} />}
    </div>
  );
}
