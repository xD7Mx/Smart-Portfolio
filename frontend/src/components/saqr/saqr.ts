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
  value: number; pl: number; pl_pct: number | null; alert?: string; marked?: string };
export type SClosed = SPos & { exit_px: number; proceeds: number; closed: string; reason: string; reason_ar: string; note?: string };
export type SSignal = { at: string; sym: string; name?: string | null; side?: "call" | "put"; verdict: "chosen" | "accepted" | "refused"; why: string; contract?: string; score?: number };
export type SLog = { at: string; kind: "buy" | "sell" | "alert" | "manual" | "info" | "error"; text: string; sym?: string | null };
export type Regime = { verdict: string; state: string; close: number; sma50: number; sma200: number; ret3m: number; chg: number | null };
export type Geo = { level: "منخفض" | "متوسط" | "مرتفع"; why: string; sectors: string[]; brent: string; n: number; at: string };
export type SaqrState = {
  market: Market; ccy: "USD" | "SAR"; regime?: Regime | null; geo?: Geo | null;
  on: boolean; capital: number; goal: number; cash: number; equity: number; pl: number; pl_pct: number | null; progress: number | null;
  started: string; tier: { frac: number; seats: number }; positions: SPos[]; closed: SClosed[]; n_closed: number; wins: number; losses: number;
  win_rate: number | null; realized: number; fees: number;
  today: { wins: number; losses: number; realized: number; new: number };
  exposure: { contracts: number; cost: number; value: number; ret: number | null };
  equity_curve: [string, number][]; signals: SSignal[]; log: SLog[]; gates: string[];
  scan?: { at: string; universe: number; movers: number; pool: number; deep: number; budget: number; tier: { frac: number; seats: number } } | null;
  session?: { state: string; label: string; detail: string; next: string | null; holiday?: string } | null;
  last_cycle: string | null; last_check: string | null;
  health: { news?: boolean; events?: boolean; quotes?: string | null; telegram?: boolean };
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
export const tone = (v: number | null | undefined) => (v == null || v === 0 ? "" : v > 0 ? "pos" : "neg");
