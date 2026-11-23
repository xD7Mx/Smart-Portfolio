/* ══ الفرص — مسحُ الرسم اليوميّ للسوق كلِّه ══ (‏D784 بأمر المالك 2026-11-22)
   «خلِّ صقر يفهم تحليلَ الرسم ويبدأ يختار بناءً عليه… يحلّل الرسمَ لكامل السوق الأمريكي ولكامل السوق السعودي فيُظهر الفرص، ويعرف جودةَ
   الفرصة لمدّة كم: بعد شهر، بعد شهرين، حتى الربع القادم… بشكلٍ يوميّ يصيد المتغيّرات ويُطلع لي قائمة… والتنفيذُ عندي، أنا اللي أختار».
   فكلُّ فرصةٍ بطاقة: نوعُها من الرسم (ارتدادٌ من الدعم · اختراقُ المقاومة · استمرارٌ بعد تصحيح…) وجودتُها من مئة ومدّتُها، ومنطقةُ الدخول
   والهدفُ والحدُّ والعائدُ إلى المخاطرة، والاتجاهُ والسيولةُ وموضعُ السعر من المناطق الثلاث، وقراءةُ الذكاء لأفضلها — وزرٌّ يفتحها في الرسم
   (وللأمريكيّ سلسلةُ عقودها). لا تنفيذَ من هنا: المالكُ يختار. والمحرّكُ في الخادم (‏services/chart_scan).
   ‏D786 (المالك: «التحليلُ الفنيّ خطوةٌ من بين الخطوات… يقرأ ويحلّل ويربط مثل الصفة البشرية»): كلُّ فرصةٍ عرضها الرسمُ تمرّ بمجلس صقر —
   المسارُ والرسمُ والنتائجُ والأخبارُ والأحداثُ والحيتانُ والمحلّلون — فتحمل البطاقةُ حكمَ كلّ عضوٍ وسطرَه، و«الرابط» يقرؤها معاً؛ وما رفضه
   عضوٌ يُعرض في «استبعدها المجلس» بسببه. */
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Crosshair, LineChart, Layers, RefreshCw, Sparkles, Check, AlertTriangle, X, Minus } from "lucide-react";
import { marketApi } from "../../services/api";
import { useAuthStore } from "../../store/authStore";
import CompanyLogo from "../common/CompanyLogo";
import OptionChain from "../market/OptionChain";
import { dday, hhmm, type Market } from "./saqr";

export type Opp = { symbol: string; name?: string | null; setup: string; side: "long" | "short"; quality: number; horizon: string; horizon_n: number;
  entry: [number, number]; target: number; stop: number; rr: number; zone: string; where: string; close: number;
  trend: { word: string; level: string; strength: number }; liq: { word?: string | null; level?: string | null; strength?: number | null; tag?: string | null };
  k: number | null; rsi: number | null; weekly?: string | null; reasons: string[]; council?: Council | null; link?: Link | null };
export type Member = { role: string; v: "ok" | "warn" | "veto" | "na"; say: string };
export type Council = { verdict: string; score: number; veto: boolean; oks: number; warns: number; members: Member[]; veto_why?: string[] };
export type Link = { decision: string; confidence: string; link: string; conflict?: string; watch?: string };
type Rejected = { symbol: string; name?: string | null; setup: string; side: string; quality: number; why: string[] };
type Scan = { market?: Market; at?: string; universe?: number; screened?: number; read?: number; found?: number; items?: Opp[]; min_q?: number;
  rejected?: Rejected[]; job: { on: boolean; msg: string; at: string | null } };

const Num = ({ v, className }: { v: string; className?: string }) => <bdi dir="ltr" className={"tabular-nums " + (className || "")}>{v}</bdi>;
const lsSet = (k: string, v: string) => { try { localStorage.setItem(k, v); } catch { /* */ } };
const p2 = (v: number) => v.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const sg = (v: number) => (v >= 0 ? "+" : "") + v.toFixed(1) + "%";
const H_OPTS: [number, string][] = [[0, "الكل"], [1, "شهر"], [2, "شهران"], [3, "حتى الربع القادم"]];
const tier = (q: number) => (q >= 75 ? "hi" : q >= 60 ? "mid" : "lo");
const V_ICON = { ok: Check, warn: AlertTriangle, veto: X, na: Minus } as const;
const V_WORD = { ok: "يوافق", warn: "يتحفّظ", veto: "يرفض", na: "غير متوفّر" } as const;

/** مجلسُ صقر على البطاقة: حكمُه ودرجتُه، وأعضاؤه السبعة بحكم كلٍّ، و«لماذا» تفتح سطرَ كلّ عضو */
function CouncilBox({ c }: { c: Council }) {
  return (
    <div className="so-council" data-role="so-council" data-verdict={c.verdict}>
      <div className="so-chead">
        <span className={"so-verdict " + (c.verdict === "يوافق" ? "ok" : "warn")} data-role="so-verdict">المجلس {c.verdict}</span>
        <span className="sq-muted">مجلسُ صقر <Num v={`${c.score}/100`} /></span>
      </div>
      <ul className="so-members" aria-label="أعضاءُ مجلس صقر">
        {c.members.map(m => {
          const I = V_ICON[m.v] || Minus;
          return <li key={m.role} data-v={m.v} data-role="so-member" title={`${m.role} — ${V_WORD[m.v]}: ${m.say}`}><I size={12} aria-hidden />{m.role}</li>;
        })}
      </ul>
      <details className="so-why" data-role="so-why">
        <summary>لماذا — ما قاله كلُّ عضو</summary>
        <ul>{c.members.map(m => <li key={m.role} data-v={m.v}><b>{m.role}</b> <small>{V_WORD[m.v]}</small> {m.say}</li>)}</ul>
      </details>
    </div>
  );
}

export default function SaqrOpps({ market }: { market: Market }) {
  const owner = useAuthStore((s: any) => s.isOwner);
  const nav = useNavigate();
  const sa = market === "sa";
  const [h, setH] = useState(0);
  const [side, setSide] = useState<"all" | "long" | "short">("all");
  const [chainFor, setChainFor] = useState<string | null>(null);
  const q = useQuery<Scan | null>({
    queryKey: ["saqr-opps", market],
    queryFn: () => marketApi.saqrOpps(market).then(r => r.data?.data ?? null),
    staleTime: 30_000, retry: 0,
    refetchInterval: qq => ((qq.state.data as Scan | null)?.job?.on ? 3_000 : false),
  });
  const run = useMutation({ mutationFn: () => marketApi.saqrOppsRun(market), onSuccess: () => setTimeout(() => q.refetch(), 600) });
  const d = q.data;
  const busy = !!d?.job?.on || run.isPending;
  const all = d?.items || [];
  const list = useMemo(() => all.filter(x => (!h || x.horizon_n === h) && (side === "all" || x.side === side)), [all, h, side]);
  const count = (n: number) => all.filter(x => (!n || x.horizon_n === n) && (side === "all" || x.side === side)).length;
  /* «افتح الرسم»: الشركةُ نفسُها في غرفة التداول — رسمُها بمناطقها الثلاث وStoch RSI ولوحتيها */
  const openChart = (sym: string) => { lsSet("sp_room_symbol", sa ? `${sym}.SR` : sym); nav("/watchlist"); };

  return (
    <div className="sq-card card card-rise so" data-role="so" data-market={market}>
      <h4><Crosshair size={14} aria-hidden /> فرصُ الرسم {d?.at && <span className="sq-muted"><Num v={`${dday(d.at)} ${hhmm(d.at)}`} /></span>}
        {owner && (
          <button type="button" className="btn-ghost sq-btn so-run" onClick={() => run.mutate()} disabled={busy} data-role="so-run"
            title={busy ? (d?.job?.msg || "يمسح") : "امسح السوقَ الآن"}>
            <RefreshCw size={14} className={busy ? "rl-spin" : ""} /> {busy ? (d?.job?.msg || "يمسح") : "امسح الآن"}
          </button>
        )}
      </h4>
      {d?.at ? (
        <p className="sq-muted" data-role="so-meta">
          قرأ <Num v={`${d.universe ?? 0}`} /> {sa ? "شركة من السوق الرئيسيّ كلِّه" : "ورقة لها عقودُ خيارات من السوق كلِّه"} · حلّل رسومَ <Num v={`${d.read ?? 0}`} /> بشموعها ·
          {" "}الفرصُ بعد مجلس صقر: <Num v={`${d.found ?? 0}`} />{(d.rejected || []).length > 0 && <> · استبعد المجلسُ <Num v={`${(d.rejected || []).length}`} /></>}
          {" "}· يُمسح كلَّ يومٍ بعد الإغلاق
        </p>
      ) : !q.isLoading && (
        <p className="sq-muted" data-role="so-none">لم يُمسح السوقُ بعد — يُمسح كلَّ يومٍ بعد إغلاقه{owner ? "، أو الآن بزرّ «امسح الآن»" : ""}.</p>
      )}
      {all.length > 0 && (
        <div className="so-filters">
          <span className="seg inline-flex" role="group" aria-label="المدّة" data-role="so-h">
            {H_OPTS.map(([n, t]) => (
              <button key={n} type="button" className={"seg-btn chip" + (h === n ? " on" : "")} aria-pressed={h === n} onClick={() => setH(n)} data-v={n}>
                {t} <Num v={`${count(n)}`} className="so-n" />
              </button>
            ))}
          </span>
          {!sa && (
            <span className="seg inline-flex" role="group" aria-label="الجهة" data-role="so-side">
              {([["all", "الجهتان"], ["long", "شراء"], ["short", "بيع"]] as const).map(([v, t]) => (
                <button key={v} type="button" className={"seg-btn chip" + (side === v ? " on" : "")} aria-pressed={side === v} onClick={() => setSide(v)} data-v={v}>{t}</button>
              ))}
            </span>
          )}
        </div>
      )}
      {d?.at && all.length === 0 && <p className="sq-muted" data-role="so-empty">لا فرصةَ بجودة <Num v={`${d.min_q ?? 50}`} /> فأكثر في مسح اليوم.</p>}
      {all.length > 0 && list.length === 0 && <p className="sq-muted" data-role="so-empty">لا فرصةَ بهذه المدّة في مسح اليوم.</p>}
      <div className="so-grid">
        {list.map((x, i) => {
          const long = x.side === "long";
          const tp = (x.target / x.close - 1) * 100, st = (x.stop / x.close - 1) * 100;
          return (
            <article key={x.symbol} className="so-card card-rise" style={{ animationDelay: `${Math.min(i, 12) * 40}ms` }} data-role="so-card" data-side={x.side} data-h={x.horizon_n}>
              <header className="op-head">
                <CompanyLogo symbol={sa ? `${x.symbol}.SR` : x.symbol} size={28} />
                <span className="op-sym"><b><Num v={x.symbol} /></b>{x.name && <small>{x.name}</small>}</span>
                <span className="so-chips">
                  <span className="sp-side" data-side={long ? "call" : "put"} data-role="so-side-chip">{long ? "شراء" : "بيع"}</span>
                  <span className="so-hz" data-role="so-hz">{x.horizon}</span>
                </span>
              </header>
              <p className="so-setup"><b data-role="so-setup">{x.setup}</b><span className="sq-muted"> · السعرُ {x.where}</span></p>
              <div className="so-q" data-tier={tier(x.quality)} data-role="so-q">
                <small>الجودة</small>
                <span className="sp-bar"><i style={{ width: `${x.quality}%` }} /></span>
                <b><bdi dir="ltr" className="tabular-nums">{x.quality}<small className="sq-muted">/100</small></bdi></b>
              </div>
              <div className="op-m">
                <span><small>منطقةُ الدخول</small><b><Num v={`${p2(x.entry[0])}–${p2(x.entry[1])}`} /></b></span>
                <span><small>الهدف</small><b className="so-pos"><Num v={p2(x.target)} /> <Num v={sg(tp)} className="so-pct" /></b></span>
                <span><small>الحدّ</small><b className="so-neg"><Num v={p2(x.stop)} /> <Num v={sg(st)} className="so-pct" /></b></span>
                <span><small>العائد ÷ المخاطرة</small><b><Num v={`${x.rr.toFixed(1)}×`} /></b></span>
                <span><small>الاتجاه</small><b>{x.trend.word} <span className="so-lv">{x.trend.level}</span></b></span>
                <span><small>السيولة</small><b>{x.liq.word || "غير متوفّرة"} {x.liq.level && <span className="so-lv">{x.liq.level}</span>}</b></span>
              </div>
              <p className="so-ind sq-muted" data-role="so-ind">
                {[x.k != null && <bdi key="k" dir="ltr" className="tabular-nums">Stoch RSI {x.k.toFixed(0)}</bdi>,
                  x.rsi != null && <bdi key="r" dir="ltr" className="tabular-nums">RSI {x.rsi.toFixed(0)}</bdi>,
                  x.weekly && <span key="w">الأسبوعيّ {x.weekly}</span>, x.liq.tag && <span key="t">{x.liq.tag}</span>]
                  .filter(Boolean).map((el, j) => <span key={j}>{j > 0 && " · "}{el}</span>)}
              </p>
              {x.council && <CouncilBox c={x.council} />}
              {x.link?.link && (
                <div className="so-ai" data-role="so-link">
                  <p><Sparkles size={13} className="ai-star" aria-hidden /> <b>الرابط: {x.link.decision}</b> <span className="sq-muted">· ثقةٌ {x.link.confidence}</span> — {x.link.link}</p>
                  {x.link.conflict && <p className="sq-muted">التعارض: {x.link.conflict}</p>}
                  {x.link.watch && <p className="sq-muted">ما يغيّر الحكم: {x.link.watch}</p>}
                </div>
              )}
              <div className="op-btns">
                <button type="button" className="btn-ghost op-act" onClick={() => openChart(x.symbol)} data-role="so-open"><LineChart size={14} /> افتح الرسم</button>
                {!sa && <button type="button" className="btn-ghost op-act" onClick={() => setChainFor(x.symbol)} data-role="so-chain"><Layers size={14} /> سلسلة العقود</button>}
              </div>
            </article>
          );
        })}
      </div>
      {(d?.rejected || []).length > 0 && (
        <details className="robo-held so-rej" data-role="so-rejected">
          <summary><span>استبعدها مجلسُ صقر (<Num v={`${(d?.rejected || []).length}`} />) — فرصٌ في الرسم رفضها عضوٌ آخر</span></summary>
          <ul>{(d?.rejected || []).map(r => (
            <li key={r.symbol} data-role="so-rej"><b><Num v={r.symbol} /></b>{r.name ? ` ${r.name}` : ""} — {r.setup}: {r.why.join(" · ")}</li>
          ))}</ul>
        </details>
      )}
      {chainFor && <OptionChain underlying={chainFor} onClose={() => setChainFor(null)} onPick={c => { setChainFor(null); lsSet("sp_room_symbol", c); nav("/watchlist"); }} />}
    </div>
  );
}
