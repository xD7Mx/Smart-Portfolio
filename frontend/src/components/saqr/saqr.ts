/* ══ صقر — حالُه المشترك بين «المحفظة» و«صقر» ══ (‏D763 بأمر المالك 2026-11-18)
   نداءٌ واحدٌ لحاله كلِّه (‏/market/saqr) يقرؤه التبويبان، ويتجدّد كلَّ خمس عشرة ثانيةً والصفحةُ ظاهرة — وكلَّ ثلاثٍ والدورةُ تعمل. */
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { marketApi } from "../../services/api";

export type Market = "us" | "sa";
export type SPos = { id: string; kind?: "option" | "stock"; name?: string | null; contract: string; symbol: string; type: "call" | "put" | "stock";
  strike: number | null; expiry: string | null; qty: number;
  entry_px: number; cost: number; opened: string; stop: number; peak: number; bid: number | null; ask: number | null; S: number | null; S0: number | null;
  target: number | null; target_label?: string | null; delta?: number | null; iv?: number | null; why: string[]; src: "saqr" | "manual"; auto: boolean;
  value: number; pl: number; pl_pct: number | null; alert?: string; marked?: string; managed?: boolean;
  owner?: boolean; tp_pct?: number | null; sl_pct?: number | null; take_x?: number | null };
export type SOrder = { id: string; contract: string; symbol: string; name?: string | null; type: "call" | "put"; strike: number; expiry: string; qty: number;
  limit: number | null; tp_pct: number | null; sl_pct: number | null; created: string; note?: string };
export type SListItem = { contract: string; symbol: string; name?: string | null; type: "call" | "put"; strike: number; expiry: string; dte: number;
  ask: number; bid: number | null; cost: number; px_src: string; spread_pct: number; breakeven: number; need_pct: number; target: number; target_label: string;
  gain_target: number; pop: number; p_touch: number; delta: number; iv: number; oi: number; score: number; tp30: { price: number; pct: number | null };
  pros: string[]; cons: string[]; margin: number; grade: string; fund: number | null; trend: { state: string; strength: number; ret3m: number | null };
  news: { impact: string; event: string } | null; price: number | null };
export type SList = { at: string; for: string; label: string; budget: number; items: SListItem[]; scanned: number; universe: number;
  excluded: Record<string, number>; cheapest: number | null; snap: boolean; calls_only: boolean; more?: boolean; levels?: Record<string, number> };
export type SClosed = SPos & { exit_px: number; proceeds: number; closed: string; reason: string; reason_ar: string; note?: string };
export type SSignal = { at: string; sym: string; name?: string | null; side?: "call" | "put"; verdict: "chosen" | "accepted" | "refused"; why: string; contract?: string; score?: number };
export type SLog = { at: string; kind: "buy" | "sell" | "alert" | "manual" | "info" | "error"; text: string; sym?: string | null };
export type Regime = { verdict: string; state: string; close: number; sma50: number; sma200: number; ret3m: number; chg: number | null };
export type Geo = { level: "منخفض" | "متوسط" | "مرتفع"; why: string; sectors: string[]; brent: string; n: number; at: string };
export type Pulse = { at: string; adv: number; dec: number; unch: number; turnover: number; leaders: [string, number][]; laggards: [string, number][];
  results: { strong: number; neutral: number; weak: number; pending: number; unknown: number }; quarter: string; brent: { px: number; chg: number; chg5: number | null } | null };
export type SaqrSettings = { per_trade: number | null; max_positions: number | null; instruments: "both" | "options" | "stocks"; sides: "both" | "calls";
  opt_stop: number; stock_stop: number; take_x: number; mode: "attack" | "balanced"; day_target: number | null; auto?: boolean };
export type DayState = { date: string | null; pl: number | null; target: number | null; hit: string | null; new: number; progress: number | null };
export type SaqrState = {
  market: Market; ccy: "USD" | "SAR"; day?: DayState | null; orders?: SOrder[]; regime?: Regime | null; geo?: Geo | null; pulse?: Pulse | null; settings?: Partial<SaqrSettings>;
  on: boolean; capital: number; goal: number; cash: number; equity: number; pl: number; pl_pct: number | null; progress: number | null;
  started: string; tier: { frac: number; seats: number }; positions: SPos[]; closed: SClosed[]; n_closed: number; wins: number; losses: number;
  win_rate: number | null; realized: number; fees: number;
  today: { wins: number; losses: number; realized: number; new: number };
  exposure: { contracts: number; cost: number; value: number; ret: number | null };
  equity_curve: [string, number][]; signals: SSignal[]; log: SLog[]; gates: string[];
  scan?: { at: string; universe: number; movers: number; pool: number; deep: number; budget: number; tier: { frac: number; seats: number };
    full?: { fallback?: boolean; cboe?: number | null; market?: number; optionable?: number; passed?: number; excluded?: Record<string, number>; up?: number; down?: number } } | null;
  session?: { state: string; label: string; detail: string; next: string | null; holiday?: string } | null;
  last_cycle: string | null; last_check: string | null;
  health: { news?: boolean; events?: boolean; quotes?: string | null };
  broker: { linked: boolean; name: string }; runs: { started: string; ended: string; capital: number; equity: number; trades: number }[];
  running: { on: boolean; msg: string; at: string | null };
  rules: any;
};

const hidden = () => typeof document !== "undefined" && document.visibilityState === "hidden";

export function useSaqr(market: Market = "us") {
  return useQuery<SaqrState | null>({
    queryKey: ["saqr", market],
    queryFn: () => marketApi.saqr(market).then(r => r.data?.data ?? null),
    staleTime: 5_000, retry: 0,
    refetchInterval: q => (hidden() ? false : (q.state.data as SaqrState | null)?.running?.on ? 3_000 : 15_000),
  });
}

/* ‏D764: السوقُ المختار يُحفظ ويتشاركه التبويبان */
const readMarket = (): Market => { try { return localStorage.getItem("sp_saqr_market") === "sa" ? "sa" : "us"; } catch { return "us"; } };
export function useSaqrMarket(): [Market, (m: Market) => void] {
  const [m, setM] = useState<Market>(readMarket);
  return [m, (v: Market) => { setM(v); try { localStorage.setItem("sp_saqr_market", v); } catch { /* */ } }];
}

/** المبلغُ بعملة السوق: «$1,234.56» و«-$21.50» للأمريكيّ، و«1,234.56 ر.س» للسعوديّ */
export const money = (ccy: string | undefined) => (v: number | null | undefined, d = 2) =>
  ccy === "SAR" ? (v == null || !isFinite(v) ? "—" : v.toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d }) + " ر.س") : usd(v, d);
export const smoney = (ccy: string | undefined) => (v: number | null | undefined, d = 2) =>
  v == null ? "—" : (v > 0 ? "+" : "") + money(ccy)(v, d);

/** «$1,234.56» و«-$21.50» — الإشارةُ قبل الرمز */
export const usd = (v: number | null | undefined, d = 2) =>
  v == null || !isFinite(v) ? "—" : (v < 0 ? "-" : "") + "$" + Math.abs(v).toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });
export const susd = (v: number | null | undefined, d = 2) => (v == null ? "—" : (v > 0 ? "+" : "") + usd(v, d));
export const spct = (v: number | null | undefined, d = 1) => (v == null || !isFinite(v) ? "—" : (v > 0 ? "+" : "") + v.toFixed(d) + "%");
export const px = (v: number | null | undefined) => (v == null ? "—" : v.toFixed(2));
const RY: Intl.DateTimeFormatOptions = { timeZone: "Asia/Riyadh" };
export const hhmm = (iso?: string | null) => {
  if (!iso) return "—";
  try { return new Date(iso).toLocaleTimeString("en-GB", { ...RY, hour: "2-digit", minute: "2-digit" }); } catch { return "—"; }
};
export const dday = (iso?: string | null) => {
  if (!iso) return "—";
  try { return new Date(iso).toLocaleDateString("en-GB", { ...RY, day: "2-digit", month: "2-digit" }); } catch { return "—"; }
};
/** «19/11 17:42» بتوقيت الرياض — تاريخُ الصفقة ووقتُها (‏D768: «بعد إيقاف تلغرام ضع تاريخ الصفقة والوقت الذي بدأت فيه») */
export const stamp = (iso?: string | null) => (iso ? `${dday(iso)} ${hhmm(iso)}` : "—");
/** المدّة: «45 د» · «3 س 10 د» · «2 ي 4 س» — حتى الآن أو حتى الخروج؛ تُعرض من اليمين (‏<Dur>) لا في حاوية الأرقام اللاتينية */
export const held = (from?: string | null, to?: string | null) => {
  if (!from) return "—";
  const m = Math.round(((to ? new Date(to).getTime() : Date.now()) - new Date(from).getTime()) / 60000);
  if (!isFinite(m)) return "—";
  const v = Math.max(0, m), d = Math.floor(v / 1440), h = Math.floor((v % 1440) / 60), mm = v % 60;
  return d ? (h ? `${d} ي ${h} س` : `${d} ي`) : h ? (mm ? `${h} س ${mm} د` : `${h} س`) : `${mm} د`;
};
export const tone = (v: number | null | undefined) => (v == null || v === 0 ? "" : v > 0 ? "pos" : "neg");
