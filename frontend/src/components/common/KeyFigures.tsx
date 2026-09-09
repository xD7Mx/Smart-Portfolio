import React from "react";
import { Shield } from "lucide-react";

/* ══ أهمُّ البيانات المالية — مكوّنٌ واحدٌ للشاشتين ══ (بأمر المالك)

   كانت شبكةُ المؤشّرات في صفحة السهم (السوق) ولا مثيلَ لها في صفحة الشركة
   (الحيازات)، فاختلف تبويبُ «نظرة عامة» بين الشاشتين. والمالكُ أمر بتوحيد
   التصميم — والتوحيدُ بمكوّنٍ واحدٍ لا بنسخةٍ مطابقةٍ اليوم تتباعد غداً.

   ولا يخترع بياناً: ما غاب من المصدر يسقط من الشبكة، وإن غاب الجميعُ قيل
   ذلك صراحةً بدل شبكةٍ فارغة. */

export type Fundamentals = {
  market_cap?: number | null;
  revenue?: number | null;
  net_income?: number | null;
  eps?: number | null;
  pe_ratio?: number | null;
  dividend_yield?: number | null;
};

const compact = (n: number) =>
  Math.abs(n) >= 1e9 ? (n / 1e9).toFixed(2) + " مليار"
  : Math.abs(n) >= 1e6 ? (n / 1e6).toFixed(1) + " مليون"
  : n.toLocaleString("en-US");

const fmt = (v: number) =>
  Number(v).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export function keyFigureRows(f: Fundamentals | null | undefined): [string, string][] {
  const src = f || {};
  return ([
    ["القيمة السوقية", src.market_cap ? compact(src.market_cap) : null],
    ["الإيرادات", src.revenue ? compact(src.revenue) : null],
    ["صافي الربح", src.net_income ? compact(src.net_income) : null],
    ["ربحية السهم EPS", src.eps != null ? fmt(src.eps) : null],
    ["مكرر الربحية P/E", src.pe_ratio ? fmt(src.pe_ratio) : null],
    ["عائد التوزيعات", src.dividend_yield != null ? fmt(src.dividend_yield) + "%" : null],
  ] as [string, string | null][]).filter(([, v]) => v != null) as [string, string][];
}

export default function KeyFigures({ fundamentals }: { fundamentals: Fundamentals | null | undefined }) {
  const rows = keyFigureRows(fundamentals);
  if (!rows.length) {
    return (
      <p className="text-[11px] text-[var(--ink-muted)] flex items-center gap-1">
        <Shield size={11} /> لا توجد بيانات مالية تفصيلية حالياً
      </p>
    );
  }
  return (
    <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
      {rows.map(([lbl, v]) => (
        <div key={lbl} className="kpi">
          <div className="kpi-lbl">{lbl}</div>
          <div className="kpi-val">{v}</div>
        </div>
      ))}
    </div>
  );
}
