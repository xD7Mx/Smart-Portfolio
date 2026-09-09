import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Sparkles, Compass, LineChart, Target, Zap, Landmark, Loader2, BookOpen } from "lucide-react";
import { aiApi } from "../../services/api";

/* لصقُ لاحقةٍ ستّ عشرية على اللون (`${color}33`) يعمل مع قيمةٍ ثابتة فقط،
   ويبطل تماماً إن كان اللون رمزاً (`var(--pos-ink)33` غير صالح) فيسقط
   الخلفية أو الحدّ بلا أثر. هذه تُنتج الشفافية بطريقةٍ تقبل الاثنين. */
const mixA = (c: string, pct: number) => `color-mix(in srgb, ${c} ${pct}%, transparent)`;


const SENTIMENT_COLOR: Record<string, string> = {
  // The unified app-wide decision vocabulary (governance Decision Engine).
  "شراء قوي": "var(--pos-ink)", "شراء": "var(--pos-ink)", "انتظار": "var(--warn-ink)", "تجنب": "var(--neg-ink)",
  // Legacy sentiment words kept as a fallback for any cached opinion.
  "متفائل": "var(--pos-ink)", "متفائل بحذر": "var(--pos-ink)", "محايد": "var(--warn-ink)",
  "متشائم بحذر": "var(--warn-ink)", "متشائم": "var(--neg-ink)",
};

function Section({ icon: Icon, color, headline, bullets }: { icon: any; color: string; headline?: string; bullets?: string[] }) {
  if (!headline && (!bullets || bullets.length === 0)) return null;
  return (
    <div className="p-3.5 rounded-xl panel">
      <p className="text-sm font-bold flex items-center gap-2 mb-2 ai-opinion-text">
        <Icon size={15} style={{ color }} /> {headline}
      </p>
      <ul className="space-y-1.5">
        {(bullets || []).map((b, i) => (
          <li key={i} className="text-xs leading-relaxed flex gap-2 ai-opinion-text">
            <span className="mt-0.5" style={{ color: "var(--ink-muted)" }}>•</span><span>{b}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/**
 * "رأي الذكاء" — one button, one fixed prompt template (only the symbol
 * changes), same idea as investing.com's WarrenAI shortcut. Renders the
 * structured sections Gemini returns; every number in them traces back to
 * our own real price/technical/fundamental data — nothing invented.
 */
export default function StockOpinion({ symbol, name }: { symbol: string; name?: string }) {
  const [asked, setAsked] = useState(false);
  const { data, isLoading, isError } = useQuery({
    queryKey: ["stock-opinion", symbol],
    queryFn: () => aiApi.stockOpinion(symbol, name).then(r => r.data.data),
    enabled: asked,
    retry: 0,
    staleTime: 24 * 60 * 60 * 1000,
  });

  if (!asked) {
    return (
      <button onClick={() => setAsked(true)}
        className="px-3 py-1.5 rounded-xl text-xs font-bold border transition-all flex items-center gap-1.5"
        style={{ borderColor: "rgba(139,92,246,.4)", color: "var(--chart-3)" }}>
        <Sparkles size={13} className="ai-star" /> رأي الذكاء بهذا السهم
      </button>
    );
  }

  if (isLoading) {
    return <div className="flex items-center gap-2 text-xs text-[var(--ink-muted)] py-2"><Loader2 size={14} className="animate-spin" /> جارٍ تحليل السهم بالذكاء الاصطناعي...</div>;
  }
  if (isError || !data) {
    return <p className="text-xs text-[var(--ink-muted)] py-2">تعذّر توليد رأي الذكاء الآن — تأكد من توفر بيانات السهم وحاول لاحقاً.</p>;
  }

  const sentColor = data.decision_color || SENTIMENT_COLOR[data.sentiment_label] || "var(--ink-muted)";
  return (
    <div className="space-y-2.5">
      <div className="p-3.5 rounded-xl" style={{ background: mixA(sentColor, 8), border: `1px solid ${mixA(sentColor, 20)}` }}>
        <p className="text-sm font-bold flex items-center gap-2 mb-2" style={{ color: sentColor }}>
          <Compass size={15} /> الرأي العام: {data.sentiment_label}
        </p>
        <ul className="space-y-1.5">
          {(data.sentiment_bullets || []).map((b: string, i: number) => (
            <li key={i} className="text-xs leading-relaxed flex gap-2 ai-opinion-text">
              <span className="mt-0.5" style={{ color: sentColor }}>•</span><span>{b}</span>
            </li>
          ))}
        </ul>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
        <Section icon={LineChart} color="var(--chart-1)" headline={data.technical_headline} bullets={data.technical_bullets} />
        <Section icon={Target} color="var(--chart-3)" headline={data.valuation_headline} bullets={data.valuation_bullets} />
        <Section icon={Zap} color="var(--warn-ink)" headline={data.fundamentals_headline} bullets={data.fundamentals_bullets} />
        <Section icon={Landmark} color="var(--pos-ink)" headline={data.dividends_headline} bullets={data.dividends_bullets} />
        {/* ══ شواهدُ «أرقام» — بيّنةٌ لا حَكَم ══ (D218)
            تُعرض كما وردت من المصدر بأسماء بيوت الخبرة وتواريخها، ولا
            يُعاد صوغها: صياغةُ الشاهد تُفسده. والقرارُ في صدر البطاقة
            يبقى قرارَ المحرّك مهما قالت. */}
        <Section icon={BookOpen} color="var(--ink-muted)" headline={data.evidence_headline} bullets={data.evidence_bullets} />
      </div>
      {/* ══ ما يعارض الحكم ══ (بأمر المالك)
          كان الحكم يعلو شواهدَ تخالفه بلا كلمة، فيُقرأ تناقضاً. وإخفاء
          المعارض كان سيُصلح المظهر ويُفسد الأداة — والمالك يستثمر بهذه
          المعلومة. فيُعرض المعارض صراحةً تحت الحكم، مسمّىً ومعدوداً. */}
      {data.tension && (
        <div className="rounded-lg p-2.5 text-[11px] leading-relaxed"
          style={{ background: "color-mix(in srgb, var(--warn-ink) 8%, transparent)",
                   border: "1px solid color-mix(in srgb, var(--warn-ink) 30%, transparent)" }}>
          <div className="font-bold mb-1" style={{ color: "var(--warn-ink)" }}>
            ما يعارض هذا الحكم ({data.tension.opposes} مقابل {data.tension.supports})
          </div>
          <ul className="space-y-0.5 text-[var(--ink)]">
            {(data.tension.against || []).map((b: string, i: number) => <li key={i}>• {b}</li>)}
          </ul>
          <div className="text-[var(--ink-muted)] mt-1">{data.tension.note}</div>
        </div>
      )}
      {data.summary && <p className="text-xs leading-relaxed pt-1 border-t border-[var(--hairline)] ai-opinion-text">{data.summary}</p>}
    </div>
  );
}
