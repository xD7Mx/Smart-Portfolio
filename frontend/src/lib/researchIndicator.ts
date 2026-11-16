/* ══ مؤشّرُ الأبحاث ══ (‏D753 · بأمر المالك 2026-11-16)
   «ضعه في الرسم عندي مؤشّراً مستقلّاً باسم مؤشّر الأبحاث — مطابقاً لمؤشّر الجزيرة كابيتال»: قرأه القارئُ البصريّ من رسم تقريرهم
   (‏scripts/audit/ajc_chart_door.py): متوسّطُ 20 ومتوسّطُ 50 وفيبوناتشي من قاع السنة إلى أوّل قمّة ارتداد (0 · 1 · 1.272 · 1.618 · 2) فوق،
   والكمّيةُ وRSI 14 تحت، وخطوطُ اتجاهٍ تصل القمم والقيعان، وأسهمُ شراءٍ وبيعٍ عند عبور RSI حدَّي 30 و70.
   وهذه الشيفرةُ نسخةٌ حرفيةٌ من `research_paper.research_ind` في الخادم (ورقةُ التقرير اليوميّ) — والحارسُ يطابق بينهما على الشموع نفسِها. */
export type RBar = { o: number; h: number; l: number; c: number; v?: number };
export type RFib = { i0: number; i1: number; p0: number; p1: number; levels: { k: number; p: number }[] };
export type RTrend = { x1: number; y1: number; x2: number; y2: number } | null;
export type RLevels = Record<string, number | string>;
export type RInd = { sma20: (number | null)[]; sma50: (number | null)[]; rsi: (number | null)[]; fib: RFib | null;
  trend: { res: RTrend; sup: RTrend }; signals: { i: number; side: "buy" | "sell" }[]; levels: RLevels };

export const RI_FIB = [0, 1, 1.272, 1.618, 2];
// الألوانُ في رموز التطبيق (‏--ri-sma20 · --ri-sma50 · --ri-fib · --ri-rsi · --ri-band · --ri-trend · --ri-buy · --ri-sell) — بمظهرَيه

function pivots(vals: number[], k = 3, high = true): number[] {
  const out: number[] = [];
  for (let j = k; j < vals.length - k; j++) {
    const w = vals.slice(j - k, j + k + 1);
    const ext = high ? Math.max(...w) : Math.min(...w);
    if (vals[j] === ext && w.filter(x => x === vals[j]).length === 1) out.push(j);
  }
  return out;
}

function rsiSeries(cl: number[], n = 14): (number | null)[] {
  const out: (number | null)[] = cl.map(() => null);
  if (cl.length <= n) return out;
  const g: number[] = [], l: number[] = [];
  for (let i = 1; i < cl.length; i++) { g.push(Math.max(0, cl[i] - cl[i - 1])); l.push(Math.max(0, cl[i - 1] - cl[i])); }
  let ag = g.slice(0, n).reduce((a, b) => a + b, 0) / n, al = l.slice(0, n).reduce((a, b) => a + b, 0) / n;
  out[n] = al === 0 ? 100 : 100 - 100 / (1 + ag / al);
  for (let i = n; i < g.length; i++) {
    ag = (ag * (n - 1) + g[i]) / n; al = (al * (n - 1) + l[i]) / n;
    out[i + 1] = al === 0 ? 100 : 100 - 100 / (1 + ag / al);
  }
  return out;
}

const argmin = (a: number, b: number, f: (i: number) => number) => { let k = a; for (let i = a; i < b; i++) if (f(i) < f(k)) k = i; return k; };
const argmax = (a: number, b: number, f: (i: number) => number) => { let k = a; for (let i = a; i < b; i++) if (f(i) > f(k)) k = i; return k; };
const mkFib = (i0: number, i1: number, p0: number, p1: number): RFib => ({ i0, i1, p0, p1, levels: RI_FIB.map(k => ({ k, p: p0 + k * (p1 - p0) })) });

/** مرساةُ فيبوناتشي: من أدنى قاعٍ في السنة إلى أوّل قمّة ارتدادٍ ذات شأن (صعودٌ 5٪ يتبعه تراجعٌ 38.2٪ منه) — ويُعاد إن تجاوز السعرُ امتدادَ 2 */
export function fibAnchor(H: number[], L: number[], C: number[], w0: number): RFib | null {
  const n = C.length, ph = pivots(H);
  let start = w0, fib: RFib | null = null;
  for (let it = 0; it < 4; it++) {
    if (start >= n - 5) break;
    const i0 = argmin(start, n, i => L[i]), p0 = L[i0];
    let pick: number | null = null;
    for (const j of ph) {
      if (j <= i0) continue;
      let nxt = n;
      for (let m = j + 1; m < n; m++) if (H[m] > H[j]) { nxt = m; break; }
      const low = nxt > j + 1 ? Math.min(...L.slice(j + 1, nxt)) : H[j];
      if ((H[j] - p0) / p0 >= 0.05 && (H[j] - low) / (H[j] - p0) >= 0.382) { pick = j; break; }
    }
    if (pick == null) break;
    fib = mkFib(i0, pick, p0, H[pick]);
    if (C[n - 1] <= p0 + 2 * (H[pick] - p0)) break;
    start = pick + 1;
  }
  if (fib == null) {
    const i0 = argmin(w0, n, i => L[i]);
    if (i0 < n - 5) {
      const i1 = argmax(i0 + 1, n, i => H[i]);
      if ((H[i1] - L[i0]) / L[i0] >= 0.03) fib = mkFib(i0, i1, L[i0], H[i1]);
    }
  }
  return fib;
}

export function psychStep(c: number): number {
  const raw = c * 0.04;
  const mag = raw > 0 ? 10 ** Math.floor(Math.log10(raw)) : 1;
  let best = mag;
  for (const m of [1, 2, 2.5, 5, 10]) if (Math.abs(m * mag - raw) < Math.abs(best - raw)) best = m * mag;
  return best;
}

const fibName = (k: number) => (k === 0 ? "قاع الموجة" : k === 1 ? "قمة الموجة" : `فيبوناتشي ${+(k * 100).toFixed(1)}٪`);

export function researchLevels(bars: RBar[], s20: number | null, s50: number | null, fib: RFib | null, pH: number[], pL: number[]): RLevels {
  const n = bars.length, { c, h, l } = bars[n - 1];
  const P = (h + l + c) / 3;
  const cl: Record<string, number> = { s3: l - 2 * (h - P), s2: P - (h - l), s1: 2 * P - h, p: P, r1: 2 * P - l, r2: P + (h - l), r3: h + 2 * (P - l) };
  const cands: [number, string][] = [];
  if (fib) for (const x of fib.levels) cands.push([x.p, fibName(x.k)]);
  if (s20) cands.push([s20, "متوسط 20"]);
  if (s50) cands.push([s50, "متوسط 50"]);
  for (const j of pH) if (j >= n - 120) cands.push([bars[j].h, "قمة سابقة"]);
  for (const j of pL) if (j >= n - 120) cands.push([bars[j].l, "قاع سابق"]);
  const step = psychStep(c), base = Math.floor(c / step) * step, real = cands.slice();
  for (const v of [0, 1, 2, 3].map(k => base - k * step).concat([1, 2, 3, 4].map(k => base + k * step)))
    if (v > 0 && !real.some(r => Math.abs(v - r[0]) / c < 0.006)) cands.push([v, "مستوى نفسي"]);
  let piv: [number, string] | null = null;
  if (fib) {
    const near = fib.levels.filter(x => Math.abs(x.p - c) / c <= 0.015 && x.k !== 0);
    if (near.length) { const x = near.reduce((a, b) => (Math.abs(b.p - c) < Math.abs(a.p - c) ? b : a)); piv = [x.p, x.k !== 1 ? fibName(x.k) : "قمة الموجة"]; }
  }
  if (!piv) piv = [cl.p, "المحور الكلاسيكي"];
  const gap = 0.004 * c;
  const side = (vals: [number, string][], below: boolean) => {
    const sorted = vals.slice().sort((a, b) => (below ? b[0] - a[0] : a[0] - b[0]));
    const out: [number, string][] = [];
    for (const [v, nm] of sorted) {
      if (Math.abs(v - piv![0]) < gap || out.some(o => Math.abs(v - o[0]) < gap)) continue;
      out.push([v, nm]);
      if (out.length === 3) break;
    }
    return out;
  };
  const sup = side(cands.filter(x => x[0] < Math.min(c, piv![0]) - gap / 2), true);
  const res = side(cands.filter(x => x[0] > Math.max(c, piv![0]) + gap / 2), false);
  for (const k of ["s1", "s2", "s3"]) if (sup.length < 3 && cl[k] < Math.min(...sup.map(s => s[0]), piv[0], c) - gap) sup.push([cl[k], "المحور الكلاسيكي"]);
  for (const k of ["r1", "r2", "r3"]) if (res.length < 3 && cl[k] > Math.max(...res.map(r => r[0]), piv[0], c) + gap) res.push([cl[k], "المحور الكلاسيكي"]);
  const out: RLevels = { p: piv[0], p_name: piv[1] };
  sup.slice(0, 3).forEach(([v, nm], i) => { out[`s${i + 1}`] = v; out[`s${i + 1}_name`] = nm; });
  res.slice(0, 3).forEach(([v, nm], i) => { out[`r${i + 1}`] = v; out[`r${i + 1}_name`] = nm; });
  return out;
}

export function researchInd(bars: RBar[]): RInd | null {
  const n = bars.length;
  if (n < 30) return null;
  const H = bars.map(b => b.h), L = bars.map(b => b.l), C = bars.map(b => b.c);
  const sma = (k: number) => C.map((_, i) => (i >= k - 1 ? C.slice(i - k + 1, i + 1).reduce((a, b) => a + b, 0) / k : null));
  const s20 = sma(20), s50 = sma(50), rsi = rsiSeries(C);
  const w0 = Math.max(0, n - 250);
  const fib = fibAnchor(H, L, C, w0);
  const pH = pivots(H), pL = pivots(L, 3, false);
  const trend: { res: RTrend; sup: RTrend } = { res: null, sup: null };
  const hs = pH.filter(j => j >= w0).reverse();
  for (let q = 0; q + 1 < hs.length; q++) {
    const b = hs[q], a = hs[q + 1];
    if (H[a] > H[b]) { const sl = (H[b] - H[a]) / (b - a); trend.res = { x1: a, y1: H[a], x2: n - 1, y2: H[a] + sl * (n - 1 - a) }; break; }
  }
  const ls = pL.filter(j => j >= w0).reverse();
  for (let q = 0; q + 1 < ls.length; q++) {
    const b = ls[q], a = ls[q + 1];
    if (L[a] < L[b]) { const sl = (L[b] - L[a]) / (b - a); trend.sup = { x1: a, y1: L[a], x2: n - 1, y2: L[a] + sl * (n - 1 - a) }; break; }
  }
  for (const k of ["res", "sup"] as const) { const t = trend[k]; if (t && !(0.85 * C[n - 1] <= t.y2 && t.y2 <= 1.15 * C[n - 1])) trend[k] = null; }
  const signals: { i: number; side: "buy" | "sell" }[] = [];
  for (let i = 1; i < n; i++) {
    const a = rsi[i - 1], b = rsi[i];
    if (a != null && b != null) { if (a < 30 && 30 <= b) signals.push({ i, side: "buy" }); else if (a > 70 && 70 >= b) signals.push({ i, side: "sell" }); }
  }
  return { sma20: s20, sma50: s50, rsi, fib, trend, signals, levels: researchLevels(bars, s20[n - 1], s50[n - 1], fib, pH, pL) };
}
