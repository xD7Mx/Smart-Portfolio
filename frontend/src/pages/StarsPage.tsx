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
  ["الشرعية", "ليست غير متوافقة"],
  ["القوائم المالية", "خلال 9 أشهر"],
  ["الخطوط الحمراء", "لا شيء"],
  ["السعر العادل", "أعلى من السعر"],
  ["نطاق السوق", "أكبر 100 شركة بالقيمة السوقية"],
  ["الترتيب", "التفوّق على تاسي 35٪ · البعد عن العادل 35٪ · الجودة 20٪ · الثقة 10٪"],
  ["السلّة", "أعلى 20 بأوزانٍ متساوية"],
  ["تحت المراقبة", "المراتب 21–30"],
  ["إعادة التوازن", "شهرياً"],
];

function MiniList({ title, items, onPick, tone: t }: { title: string; items: any[]; onPick: (s: string) => void; tone: string }) {
  if (!items?.length) return null;
  return (
    <div className="card p-0">
      <div className="flex items-center justify-between px-4 pt-4 pb-2">
        <p className="card-title" style={{ color: t }}>{title}</p>
        <span className="text-[12px] text-[var(--ink-muted)] tabular-nums">{items.length}</span>
      </div>
      {items.map((m: any) => (
        <button key={m.symbol} type="button" onClick={() => onPick(m.symbol)}
          className="w-full flex items-center gap-2 px-4 py-2 min-h-[44px] text-start border-t border-[var(--hairline)] hover:bg-[var(--field)]">
          <CompanyLogo symbol={m.symbol} size={24} />
          <span className="flex-1 min-w-0">
            <span className="block text-[13px] font-semibold text-[var(--ink)] truncate">{m.name}</span>
            <span className="block text-[11px] text-[var(--ink-muted)] tabular-nums" dir="ltr" style={{ textAlign: "right" }}>{m.symbol}</span>
          </span>
          {typeof m.rank === "number" && <span className="text-[12px] font-bold tabular-nums text-[var(--ink-muted)]" dir="ltr">#{m.rank}</span>}
        </button>
      ))}
    </div>
  );
}

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
              {info("التوازنُ القادم", data.next_rebalance || data.rebalance || "شهرياً")}
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

      {data?.members?.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <MiniList title="قادمة هذا الشهر" items={data.entering} onPick={setSheet} tone="var(--pos-ink)" />
          <MiniList title="خارجة هذا الشهر" items={data.exiting} onPick={setSheet} tone="var(--neg-ink)" />
        </div>
      )}
      {data?.members?.length > 0 && <MiniList title="تحت المراقبة" items={data.watch} onPick={setSheet} tone="var(--warn-ink)" />}

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
