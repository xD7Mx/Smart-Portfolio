/**
 * Governance — portfolio-wide oversight, not a single-stock search (that
 * lives in AIPage/CompanyPage already). Every number here is a roll-up
 * across ALL holdings at once: is the portfolio, as a whole, safe and
 * under control? Answers that question visually, in one glance.
 */
import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Shield, ShieldCheck, ShieldAlert, AlertTriangle, Layers, TrendingUp, Landmark, Sparkles } from "lucide-react";
import { ResponsiveContainer, Tooltip, AreaChart, Area, XAxis, YAxis, CartesianGrid } from "recharts";
import { portfolioApi } from "../services/api";
import CompanyLogo from "../components/common/CompanyLogo";
import GovernanceV2Modal from "../components/governance/GovernanceV2Modal";
import clsx from "clsx";

/* اللوحة الأساسية الأولى (ما قبل 3d96cf1) بترتيبها الأصلي، لكنْ بالرموز
   لا بقيمٍ ثابتة: القيمة الثابتة لا تعرف المظهر ولا يطالها تغييرٌ لاحق.
   وأُخرجت منها أحبار الدلالة التي كانت مدسوسةً في مواضع ٣ و٦: الأخضر
   والأحمر هنا يقولان «القطاع رقم ٣» وهو معنًى لا يملكانه — والقاعدة
   نفسها هي ما جعل الأشرطة تُقرأ صارخةً. */
const COLORS = ["var(--chart-1)", "var(--chart-2)", "var(--chart-3)", "var(--chart-4)", "var(--chart-5)", "var(--chart-6)", "var(--chart-7)", "var(--chart-9)"];
/* ألوان الحكم من رموز التطبيق لا قيماً ثابتة (المعيار 12): «var(--neg-ink)» على
   ورق المظهر الفاتح كان 3.41:1 — تحت أرضية 4.5:1 لنصٍّ يحمل حكم المحفظة كلها.
   الرموز مضبوطة للمظهرين معاً. */
const scoreColor = (s: number | null) => s == null ? "var(--ink-muted)"
  : s >= 70 ? "var(--pos-ink)" : s >= 50 ? "var(--warn-ink)" : "var(--neg-ink)";
const fmt0 = (n: number) => (n ?? 0).toLocaleString("en-US", { maximumFractionDigits: 0 });

function ScoreGauge({ score, label, color }: { score: number | null; label: string; color: string }) {
  const size = 128;
  const pct = score ?? 0;
  return (
    <div className="flex items-center gap-4">
      <div className="relative inline-flex items-center justify-center shrink-0" style={{ width: size, height: size }}>
        <svg className="-rotate-90" width={size} height={size} viewBox="0 0 36 36">
          <circle cx="18" cy="18" r="15.9" fill="none" stroke="var(--hairline)" strokeWidth="3.2" />
          {score != null && (
            <circle cx="18" cy="18" r="15.9" fill="none" stroke={color} strokeWidth="3.2"
              strokeDasharray={`${pct} ${100 - pct}`} strokeLinecap="round" />
          )}
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="font-extrabold text-[var(--ink)] leading-none text-3xl">{score ?? "—"}</span>
          <span className="text-[var(--ink-muted)] text-xs">/100</span>
        </div>
      </div>
      <div>
        <p className="text-xs text-[var(--ink-muted)] mb-1">الحالة العامة للمحفظة</p>
        <p className="text-lg font-bold" style={{ color }}>{label}</p>
      </div>
    </div>
  );
}

function TopDividendsChart({ rows }: { rows: any[] }) {
  const data = [...(rows || [])]
    .filter(r => (r.total_dividends_received || 0) > 0)
    .sort((a, b) => b.total_dividends_received - a.total_dividends_received)
    .slice(0, 6)
    .map(r => ({ name: r.name, value: r.total_dividends_received, symbol: r.symbol }));
  const max = Math.max(...data.map(d => d.value), 1);

  return (
    <div className="card h-full flex flex-col">
      <p className="card-title mb-3 flex items-center gap-1.5"><Landmark size={14} className="text-[var(--warn-ink)]" /> الأسخى بالتوزيعات</p>
      {data.length === 0 ? (
        <div className="py-8 text-center text-[var(--ink-muted)] text-sm">لا توجد توزيعات مستلمة حتى الآن</div>
      ) : (
        <div className="flex items-end gap-3 flex-1 min-h-[190px]">
          {data.map((d, i) => (
            <div key={d.symbol} className="flex-1 min-w-0 flex flex-col items-center justify-end h-full">
              <span className="text-[11px] font-bold text-[var(--ink)] mb-1 truncate max-w-full">{fmt0(d.value)}</span>
              <div
                className="w-full rounded-t-lg relative overflow-hidden"
                style={{
                  height: `${Math.max((d.value / max) * 100, 4)}%`,
                  /* ══ لونٌ لكل شركة ══ (بأمر المالك)
                     وُحّدت الأعمدة على الكهرمانيّ حيناً، فأمر المالك بردّ
                     الألوان. ولوحة التصنيف (‏--chart-1..9) هي ما كانت
                     عليه، فرُدّت كما كانت: العمود يأخذ درجته بترتيبه،
                     والشعار أسفله يربط الدرجة بصاحبها. */
                  background: `linear-gradient(180deg, color-mix(in srgb, ${COLORS[i % COLORS.length]} 100%, white 25%) 0%, ${COLORS[i % COLORS.length]} 60%, color-mix(in srgb, ${COLORS[i % COLORS.length]} 100%, black 20%) 100%)`,
                  borderRadius: "8px 8px 3px 3px",
                }}
              >
                <div className="absolute top-0 inset-x-0 h-2/5" style={{ background: "transparent, transparent)" }} />
              </div>
              {/* الشعار بدل الاسم: ستّة أعمدة على عرض الجوّال لا تترك للاسم
                  إلا نحواً من خمسين بكسل، فيُبتر ولا يُعرف منه شيء. الاسم
                  الكامل يبقى في التلميح، ومن لا شعار له يعود رمزه نصّاً. */}
              <div className="mt-1.5 flex justify-center" title={d.name} aria-label={d.name}>
                <CompanyLogo symbol={d.symbol} size={20} />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function SectorConcentration({ sectors }: { sectors: { sector: string; weight_pct: number }[] }) {
  /* كل القطاعات لا أعلى ستّة: هذه بطاقة «تركّز»، والتركّز لا يُقرأ من جزءٍ من
     التوزيع. كان القصّ صامتاً وبلا كلمة «أعلى» في العنوان، فمحفظةٌ بسبعة
     قطاعات تُقرأ كأنها ستّة — وأصغر قطاع (وهو غالباً محلّ السؤال عن التنويع)
     هو أوّل ما يختفي. وهي أشرطة رأسية فلا يُثقل طولها الصفحة.
     ملاحظة: «الأسخى بالتوزيعات» يبقى بستّة لأن عنوانه يَعِد بالأعلى صراحةً. */
  const list = sectors || [];
  const max = Math.max(...list.map(s => s.weight_pct), 1);
  return (
    <div className="card">
      <p className="card-title mb-3 flex items-center gap-1.5"><Layers size={14} className="text-[var(--brand-ink)]" /> التركّز القطاعي</p>
      {list.length === 0 ? <div className="py-8 text-center text-[var(--ink-muted)] text-sm">لا توجد بيانات حالياً</div> : (
        <div className="space-y-2.5">
          {list.map((s, i) => {
            const color = COLORS[i % COLORS.length];
            const pct = Math.max((s.weight_pct / max) * 100, 8);
            return (
              <div key={s.sector}>
                <p className={clsx("text-xs font-bold mb-1 truncate", s.weight_pct >= 30 ? "text-[var(--warn-ink)]" : "text-[var(--ink)]")}>{s.sector}</p>
                <div className="flex items-center gap-2.5">
                  <div className="shrink-0 w-[22px] h-[22px] rounded-full flex items-center justify-center text-[10px] font-bold text-[var(--ink)]" style={{ background: "var(--track)" }}>
                    {i + 1}
                  </div>
                  <div className="relative flex-1 min-w-0 h-5 rounded-full" style={{ background: "var(--track)" }}>
                    <div
                      className="absolute inset-y-0 start-0 rounded-full overflow-hidden"
                      style={{
                        width: `${pct}%`,
                        background: `linear-gradient(90deg, color-mix(in srgb, ${color} 100%, white 20%) 0%, ${color} 55%, color-mix(in srgb, ${color} 100%, black 20%) 100%)`,
                      }}
                    />
                  </div>
                  {/* ══ النسبة خارج الشريط ══
                      كانت داخله في «أنبوبةٍ» سوداء بعتامة ٧٨٪ — واستقبحها
                      المالك بحقّ. ولم تكن عبثاً: الأبيض على ألوان الأشرطة
                      يهبط إلى 1.62:1 عند أفتح طرفٍ في التدرّج، فلا يُقرأ
                      إطلاقاً بلا تلك الأرضية.
                      فبدل ترقيع الأرضية أو تركِ الرقم غير مقروء، خرج الرقم
                      إلى أرضية البطاقة نفسها: لا سوادَ، ولا رقعةَ لون تحت
                      نصّ — ويرث تباين البطاقة العالي كأيّ رقمٍ آخر. */}
                  <span className="shrink-0 w-[46px] text-start text-[11px] font-extrabold tabular-nums text-[var(--ink)]">
                    {s.weight_pct}%
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function AttentionList({ items }: { items: { severity: string; symbol: string | null; name: string | null; message: string }[] }) {
  return (
    <div className="card">
      <p className="card-title mb-3 flex items-center gap-1.5"><AlertTriangle size={14} className="text-[var(--warn-ink)]" /> يحتاج انتباهك</p>
      {(items || []).length === 0 ? (
        <div className="py-8 text-center text-[var(--pos-ink)] text-sm flex flex-col items-center gap-2">
          <ShieldCheck size={28} />
          لا توجد تنبيهات حالياً — محفظتك تحت السيطرة
        </div>
      ) : (
        <ul className="space-y-2">
          {(items || []).map((a, i) => (
            <li key={i} className="flex items-start gap-2 text-xs p-2.5 rounded-lg"
              /* أرضيةُ التنبيه تُشتقّ من رمز الحالة نفسه، لا من لونٍ مكتوب
                 بيده: كانت ‎rgba(244,63,94) — أحمرَ ورديّاً من عائلةٍ أخرى
                 يجلس تحت علامةٍ لونُها `--neg-ink`، فيختلف الظرف عن مظروفه
                 في العنصر الواحد. وهي كذلك لا تتبع المظهر ولا تتغيّر متى
                 غيّر المالك درجته. */
              style={{ background: a.severity === "high"
                ? "color-mix(in srgb, var(--neg-ink) 8%, transparent)"
                : "color-mix(in srgb, var(--warn-ink) 8%, transparent)" }}>
              <span className="mt-0.5" style={{ color: a.severity === "high" ? "var(--neg-ink)" : "var(--warn-ink)" }}>⚠</span>
              <span className="text-[var(--ink)]">
                {a.name && <span className="font-bold text-[var(--ink)]">{a.name} — </span>}
                {a.message}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function HoldingsHeatmap({ rows, onOpenV2 }: { rows: any[]; onOpenV2: (symbol: string, name: string) => void }) {
  const nav = useNavigate();
  return (
    <div className="card">
      <p className="card-title mb-3 flex items-center gap-1.5"><Shield size={14} className="text-[var(--brand-ink)]" /> سلامة كل شركة في محفظتك</p>
      {(rows || []).length === 0 ? <div className="py-8 text-center text-[var(--ink-muted)] text-sm">لا توجد بيانات حالياً</div> : (
        <div className="space-y-2">
          {(rows || []).map((r: any) => (
            <div key={r.id} className="w-full flex items-center gap-3 p-2 rounded-xl hover:panel transition-colors">
              <button onClick={() => nav(`/portfolio/${r.id}`)} className="flex items-center gap-3 flex-1 min-w-0 text-start">
                <CompanyLogo symbol={r.symbol} size={28} />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-[var(--ink)] text-sm font-semibold truncate">{r.name}</span>
                    <span className="tag-b shrink-0">{r.symbol}</span>
                    {r.sharia_status === "NON_COMPLIANT" && <span className="tag-r shrink-0">غير متوافقة</span>}
                  </div>
                  {r.insufficient_data ? (
                    <div className="mt-1.5 text-[10px] text-[var(--ink-muted)]">بانتظار وصول القوائم</div>
                  ) : (
                    <div className="h-1.5 rounded-full bg-[var(--surface)] mt-1.5">
                      <div className="h-1.5 rounded-full" style={{ width: `${r.finance_score ?? 0}%`, background: scoreColor(r.finance_score) }} />
                    </div>
                  )}
                </div>
              </button>
              <button onClick={() => onOpenV2(r.symbol, r.name)} title="ميزان خبراء الحوكمة"
                className="shrink-0 p-1.5 rounded-lg text-[var(--brand-ink)]">
                <Sparkles size={15} className="ai-star" />
              </button>
              <div className="text-end shrink-0">
                <div className="font-bold text-sm" style={{ color: r.insufficient_data ? "var(--ink-muted)" : scoreColor(r.finance_score) }}>
                  {r.insufficient_data ? "—" : (r.finance_score != null ? Math.round(r.finance_score) : "—")}
                </div>
                <div className="text-[10px] text-[var(--ink-muted)]">{r.weight_pct}% من المحفظة</div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function GovernanceTrend() {
  const { data: hist = [] } = useQuery({
    queryKey: ["portfolio-history"],
    queryFn: () => portfolioApi.history().then(r => Array.isArray(r.data?.data) ? r.data.data : []),
  });
  const points = hist.filter((p: any) => p.governance_score != null);
  return (
    <div className="card">
      <p className="card-title mb-3 flex items-center gap-1.5"><TrendingUp size={14} className="text-[var(--brand-ink)]" /> اتجاه درجة الجودة المالية عبر الزمن</p>
      {points.length >= 2 ? (
        <div style={{ height: 140 }} dir="ltr">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={points} margin={{ top: 6, right: 6, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="govScoreGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--chart-3)" stopOpacity={0.35} />
                  <stop offset="100%" stopColor="var(--chart-3)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,.12)" />
              <XAxis dataKey="date" tick={{ fontSize: 10, fill: "var(--ink-muted)" }} tickFormatter={(d: string) => d.slice(5)} />
              <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: "var(--ink-muted)" }} width={28} />
              <Tooltip contentStyle={{ background: "var(--pop)", border: "1px solid var(--line)", color: "var(--tip-text)", borderRadius: 10, fontSize: 12 }}
                labelStyle={{ color: "var(--tip-text)", fontWeight: 300, marginBottom: 4 }}
                itemStyle={{ color: "var(--tip-text)" }}
                formatter={(v: any) => [`${v}/100`, "درجة الجودة المالية"]} />
              <Area type="monotone" dataKey="governance_score" stroke="var(--chart-3)" strokeWidth={2} fill="url(#govScoreGrad)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="py-8 text-center text-[var(--ink-muted)] text-sm">
          {points.length === 1 ? "سُجلت أول لقطة — يكتمل الرسم مع الأيام القادمة" : "لا توجد بيانات تاريخية بعد — تُبنى تلقائياً مع مرور الأيام"}
        </div>
      )}
    </div>
  );
}

function MarketOpportunities() {
  const { data, isLoading } = useQuery({
    queryKey: ["governance-market"],
    queryFn: () => portfolioApi.governanceMarket().then(r => r.data.data),
  });
  const scoreColorLocal = (s: number) => s >= 70 ? "var(--pos-ink)" : s >= 45 ? "var(--warn-ink)" : "var(--neg-ink)";
  const shariaBadge = (status: string) => status === "COMPLIANT"
    ? <span className="tag-g" style={{ fontSize: 10 }}>متوافقة شرعياً</span>
    : status === "NON_COMPLIANT"
    ? <span className="tag-r" style={{ fontSize: 10 }}>غير متوافقة</span>
    : <span className="tag-n" style={{ fontSize: 10 }}>غير معروف</span>;

  if (isLoading) return <div className="card"><div className="h-40 skeleton" /></div>;
  if (!data?.has_data) {
    return (
      <div className="card">
        <div className="py-16 text-center text-[var(--ink-muted)]">
          <ShieldAlert size={40} className="mx-auto mb-3 opacity-30" />
          <p className="text-sm">تعذّر فحص السوق حالياً — حاول مجدداً بعد قليل</p>
        </div>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-3">
        <p className="card-title">فرص السوق</p>
        <span className="text-[11px] text-[var(--ink-muted)]">
          {data.scored_count} من {data.scanned_count} (استُبعد {data.excluded_held_count} مملوكة فعلاً)
        </span>
      </div>
      <div className="space-y-1.5 max-h-[520px] overflow-y-auto">
        {(data.opportunities || []).map((o: any) => (
          <div key={o.symbol} className="flex items-center gap-3 p-2.5 rounded-xl hover:panel transition-colors">
            <CompanyLogo symbol={o.symbol} size={30} logoUrl={o.logo_url} />
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <span className="text-[var(--ink)] text-sm font-semibold truncate">{o.name}</span>
                <span className="tag-b shrink-0" style={{ fontSize: 10 }}>{o.symbol}</span>
                {shariaBadge(o.sharia_status)}
              </div>
              <div className="text-[11px] text-[var(--ink-muted)] mt-0.5">{o.sector}</div>
            </div>
            <div className="text-end shrink-0">
              <div className="font-bold text-sm" style={{ color: scoreColorLocal(o.finance_score) }}>{Math.round(o.finance_score)}/100</div>
              <div className="text-[10px] text-[var(--ink-muted)]">سلامة مالية</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function GovernancePage() {
  const [mode, setMode] = useState<"portfolio" | "market">("portfolio");
  const [v2Target, setV2Target] = useState<{ symbol: string; name: string } | null>(null);
  const { data, isLoading } = useQuery({
    queryKey: ["portfolio-governance"],
    queryFn: () => portfolioApi.governance().then(r => r.data.data),
    enabled: mode === "portfolio",
  });

  return (
    <div className="space-y-5 fade-in">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-2.5 flex-wrap">
          <h1 className="text-2xl font-medium text-[var(--ink)]">الحوكمة</h1>
        </div>
        <div className="flex items-center gap-1 p-1 rounded-xl" style={{ background: "var(--panel)" }}>
          <button onClick={() => setMode("portfolio")}
            className={mode === "portfolio" ? "px-3 py-1.5 rounded-lg text-xs font-bold text-[var(--brand-ink)]" : "px-3 py-1.5 rounded-lg text-xs text-[var(--ink-muted)] hover:text-[var(--ink)]"}
            style={mode === "portfolio" ? { background: "transparent,rgba(139,92,246,.12))", border: "1px solid var(--hairline)" } : undefined}>
            محفظتي
          </button>
          <button onClick={() => setMode("market")}
            className={mode === "market" ? "px-3 py-1.5 rounded-lg text-xs font-bold text-[var(--brand-ink)]" : "px-3 py-1.5 rounded-lg text-xs text-[var(--ink-muted)] hover:text-[var(--ink)]"}
            style={mode === "market" ? { background: "transparent,rgba(139,92,246,.12))", border: "1px solid var(--hairline)" } : undefined}>
            السوق
          </button>
        </div>
      </div>

      {mode === "market" ? <MarketOpportunities /> : isLoading ? (
        <div className="card"><div className="h-40 skeleton" /></div>
      ) : !data?.has_data ? (
        <div className="card">
          <div className="py-16 text-center text-[var(--ink-muted)]">
            <ShieldAlert size={40} className="mx-auto mb-3 opacity-30" />
            <p className="text-sm">أضف شركات إلى محفظتك لتظهر الرقابة الشاملة تلقائياً</p>
          </div>
        </div>
      ) : (
        <>
          <div className="card">
            <ScoreGauge score={data.overall_score} label={data.overall_label} color={data.overall_color} />
            {data.overall_narrative && (
              <p className="mt-4 pt-4 text-xs text-[var(--ink)] leading-relaxed" style={{ borderTop: "1px solid var(--hairline)" }}>
                {data.overall_narrative}
              </p>
            )}
          </div>

          <GovernanceTrend />

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <TopDividendsChart rows={data.holdings} />
            <SectorConcentration sectors={data.sectors} />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <HoldingsHeatmap rows={data.holdings} onOpenV2={(symbol, name) => setV2Target({ symbol, name })} />
            <AttentionList items={data.attention} />
          </div>
        </>
      )}

      {v2Target && (
        <GovernanceV2Modal symbol={v2Target.symbol} name={v2Target.name} onClose={() => setV2Target(null)} />
      )}
    </div>
  );
}
