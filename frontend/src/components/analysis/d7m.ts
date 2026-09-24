/* ══ مؤشّر D7M — ترجمةُ سكربت المالك (Pine v6) إلى حسابٍ على شموع التطبيق ══
 *
 * يُنقل منه ما يُبنى على شموع السهم نفسِها:
 *   · الفيبوناتشي التلقائي من الزجزاج (انحرافٌ = ATR(10)÷السعر×100×3 · عمق 7)
 *     بمستوياته وألوانه ونصوص مناطقه كما في السكربت.
 *   · القناة السعرية التلقائية (آخرُ ثلاث قممٍ/قيعانٍ للزجزاج بعمق 20).
 * ولا يُنقل ما يحتاج إطاراتٍ لحظيةً أو بياناتٍ أمريكية (لوحةُ الاتجاه وأداةُ
 * الصفقة وVIX والأخبار) — لا تُختلق بياناتٌ لا نملكها.
 */

export type Bar = { date: string; open: number; high: number; low: number; close: number };
export type Pivot = { index: number; price: number; isHigh: boolean };

/** ATR بطريقة Pine (RMA لمدى الحقيقيّ). */
export function atr(bars: Bar[], len = 10): number[] {
  const out: number[] = [];
  let prev: number | null = null;
  bars.forEach((b, i) => {
    const pc = i > 0 ? bars[i - 1].close : b.close;
    const tr = Math.max(b.high - b.low, Math.abs(b.high - pc), Math.abs(b.low - pc));
    prev = prev == null ? tr : (prev * (len - 1) + tr) / len;
    out.push(prev);
  });
  return out;
}

/**
 * زجزاجُ TradingView (مكتبة ZigZag/7) مبسّطاً بأمانة:
 *   · القمّةُ/القاعُ محوريٌّ بـ`depth` شمعةً على كلّ جانبٍ نصفاً.
 *   · يُقبل المحورُ الجديدُ إذا خالف اتجاهَ السابق وابتعد عنه بنسبة الانحراف،
 *     ويُستبدَل السابقُ إذا كان من جنسه وأشدَّ منه.
 */
export function zigzag(bars: Bar[], mult: number, depth: number): Pivot[] {
  const n = bars.length;
  if (n < depth + 2) return [];
  const a = atr(bars, 10);
  const half = Math.max(1, Math.floor(depth / 2));
  const piv: Pivot[] = [];
  for (let i = half; i < n - half; i++) {
    let isH = true, isL = true;
    for (let k = i - half; k <= i + half; k++) {
      if (k === i) continue;
      if (bars[k].high > bars[i].high) isH = false;
      if (bars[k].low < bars[i].low) isL = false;
    }
    const dev = (a[i] / bars[i].close) * 100 * mult;
    for (const [ok, price, isHigh] of [[isH, bars[i].high, true], [isL, bars[i].low, false]] as const) {
      if (!ok) continue;
      const last = piv[piv.length - 1];
      if (!last) { piv.push({ index: i, price, isHigh }); continue; }
      if (last.isHigh === isHigh) {
        if (isHigh ? price > last.price : price < last.price) piv[piv.length - 1] = { index: i, price, isHigh };
        continue;
      }
      if (Math.abs(price - last.price) / last.price * 100 >= dev) piv.push({ index: i, price, isHigh });
    }
  }
  return piv;
}

/** مستوياتُ السكربت الظاهرةُ افتراضاً: [القيمة، اللون، النصّ]. */
/* دورُ اللون لا قيمتُه — يُترجَم إلى رموز التطبيق عند الرسم. */
const WHITE = "white", YELLOW = "yellow";
export const FIB_LEVELS: [number, string][] = [
  [0, WHITE], [0.5, WHITE], [0.618, YELLOW], [-0.5, WHITE], [1.5, WHITE], [1, WHITE],
  [-1, WHITE], [-0.618, YELLOW], [1.618, YELLOW], [-0.1, WHITE], [1.1, WHITE], [2, WHITE],
  [2.1, WHITE], [-1.1, WHITE],
];

export type FibLine = { price: number; level: number; color: string; title: string };
export type FibZone = { price: number; title: string };

/** الفيبوناتشي التلقائي: آخرُ ضلعٍ للزجزاج (بلا عكس) ومستوياتُه ومناطقُه. */
export function autoFib(bars: Bar[], mult = 3, depth = 7, reverse = false): { lines: FibLine[]; zones: FibZone[]; startIndex: number } | null {
  const p = zigzag(bars, mult, depth);
  if (p.length < 2) return null;
  const start = p[p.length - 2], end = p[p.length - 1];
  const startPrice = reverse ? start.price : end.price, endPrice = reverse ? end.price : start.price;
  const height = (startPrice > endPrice ? -1 : 1) * Math.abs(startPrice - endPrice);
  const lines = FIB_LEVELS.map(([lv, color]) => {
    const price = startPrice + height * lv;
    const name = lv === 0.618 ? "اتجاه معاكس" : lv === 0.5 ? "دعــم قـوي" : "";
    return { price, level: lv, color, title: name };
  });
  // مناطقُ السكربت بين المستويات الرئيسية 0 · 1 · 1.1 · -0.1
  const main = [0, 1, 1.1, -0.1].map(lv => startPrice + height * lv).sort((x, y) => x - y);
  const mid = (startPrice + endPrice) / 2;
  const zones: FibZone[] = [];
  for (let i = 0; i < main.length - 1; i++) {
    const lo = main[i], hi = main[i + 1], mz = (lo + hi) / 2;
    const upper = mz >= mid;
    const isRes = upper && lo === main[main.length - 2];
    const isLowSup = mz < mid && hi === main[1];
    const isUpSup = upper && !isRes;
    if (isRes) zones.push({ price: mz, title: "الــمــقــاومــة" });
    else if (isUpSup) zones.push({ price: mz, title: "لاتطمع - لاتعكس" });
    else if (isLowSup) zones.push({ price: mz, title: "الـــدعـــم" });
  }
  return { lines, zones, startIndex: start.index };
}

export type Channel = { base: [number, number][]; parallel: [number, number][] };

/** القناةُ التلقائية: قاعدةٌ بين المحورين المتجانسين الأخيرين، وموازيةٌ من الأوسط. */
export function autoChannel(bars: Bar[], mult = 3, depth = 20): Channel | null {
  const p = zigzag(bars, mult, depth);
  if (p.length < 3) return null;
  const a = p[p.length - 3], b = p[p.length - 2], c = p[p.length - 1];
  if (a.isHigh !== c.isHigh || a.index === c.index) return null;
  const slope = (c.price - a.price) / (c.index - a.index);
  const icBase = a.price - slope * a.index;
  const icPar = b.price - slope * b.index;
  const xEnd = bars.length - 1;
  return {
    base: [[a.index, a.price], [xEnd, slope * xEnd + icBase]],
    parallel: [[b.index, b.price], [xEnd, slope * xEnd + icPar]],
  };
}

/* ══════════════════════════════════════════════════════════════════════
 * ما يلي: بقيّةُ السكربت — المتوسّطات · VWAP · ADX · السيولة · MACD الذكي ·
 * الترند التلقائي · لوحةُ الاتجاه · التنبيهات · أداةُ الصفقة.
 * ══════════════════════════════════════════════════════════════════════ */
export type VBar = Bar & { volume?: number };

export function ema(src: number[], len: number): (number | null)[] {
  const k = 2 / (len + 1); let prev: number | null = null;
  return src.map((v, i) => {
    if (i < len - 1) return null;
    if (prev == null) { prev = src.slice(0, len).reduce((a, b) => a + b, 0) / len; return prev; }
    prev = v * k + prev * (1 - k); return prev;
  });
}
export function rma(src: number[], len: number): (number | null)[] {
  let prev: number | null = null;
  return src.map((v, i) => {
    if (i < len - 1) return null;
    if (prev == null) { prev = src.slice(0, len).reduce((a, b) => a + b, 0) / len; return prev; }
    prev = (prev * (len - 1) + v) / len; return prev;
  });
}
export function sma(src: number[], len: number): (number | null)[] {
  return src.map((_, i) => i < len - 1 ? null : src.slice(i - len + 1, i + 1).reduce((a, b) => a + b, 0) / len);
}

/** ta.dmi(len, smooth) → [+DI, −DI, ADX] */
export function dmi(bars: Bar[], len = 14, smooth = 14) {
  const pdm: number[] = [], ndm: number[] = [], tr: number[] = [];
  bars.forEach((b, i) => {
    if (i === 0) { pdm.push(0); ndm.push(0); tr.push(b.high - b.low); return; }
    const up = b.high - bars[i - 1].high, dn = bars[i - 1].low - b.low;
    pdm.push(up > dn && up > 0 ? up : 0); ndm.push(dn > up && dn > 0 ? dn : 0);
    const pc = bars[i - 1].close;
    tr.push(Math.max(b.high - b.low, Math.abs(b.high - pc), Math.abs(b.low - pc)));
  });
  const trr = rma(tr, len), p = rma(pdm, len), n = rma(ndm, len);
  const plus = p.map((v, i) => v == null || !trr[i] ? null : 100 * v / trr[i]!);
  const minus = n.map((v, i) => v == null || !trr[i] ? null : 100 * v / trr[i]!);
  const dx = plus.map((v, i) => v == null || minus[i] == null ? 0 : (v + minus[i]! === 0 ? 0 : 100 * Math.abs(v - minus[i]!) / (v + minus[i]!)));
  const adx = rma(dx, smooth);
  return { plus, minus, adx };
}

/** VWAP بمرسى (Session/Week/Month/Year) على شموع يومية، ونطاقُ انحرافه المعياريّ. */
export function vwapAnchored(bars: VBar[], anchor: "Session" | "Week" | "Month" | "Year" = "Session", mult = 1) {
  const key = (d: string) => {
    const dt = new Date(d.slice(0, 10) + "T00:00:00Z");
    if (anchor === "Session") return d.slice(0, 10);
    if (anchor === "Month") return d.slice(0, 7);
    if (anchor === "Year") return d.slice(0, 4);
    const w = new Date(dt); w.setUTCDate(dt.getUTCDate() - ((dt.getUTCDay() + 1) % 7)); return w.toISOString().slice(0, 10);
  };
  let k0 = "", cs = 0, cv = 0, csq = 0;
  const v: number[] = [], up: number[] = [], lo: number[] = [];
  bars.forEach(b => {
    const src = (b.high + b.low + b.close) / 3, vol = b.volume && b.volume > 0 ? b.volume : 1;
    const k = key(b.date);
    if (k !== k0) { k0 = k; cs = 0; cv = 0; csq = 0; }
    cs += src * vol; cv += vol;
    const vw = cs / cv; const dev = src - vw; csq += dev * dev * vol;
    const sd = Math.sqrt(csq / cv);
    v.push(vw); up.push(vw + sd * mult); lo.push(vw - sd * mult);
  });
  return { vwap: v, upper: up, lower: lo };
}

/** إطارٌ أعلى من شموعٍ يومية: أسبوعيّ أو شهريّ (لآخر شمعةٍ في كلّ فترة). */
export function resample(bars: VBar[], unit: "W" | "M"): VBar[] {
  const out: VBar[] = [];
  for (const b of bars) {
    const dt = new Date(b.date.slice(0, 10) + "T00:00:00Z");
    let k: string;
    if (unit === "M") k = b.date.slice(0, 7);
    else { const w = new Date(dt); w.setUTCDate(dt.getUTCDate() - ((dt.getUTCDay() + 1) % 7)); k = w.toISOString().slice(0, 10); }
    const last = out[out.length - 1] as any;
    if (last && last._k === k) {
      last.high = Math.max(last.high, b.high); last.low = Math.min(last.low, b.low);
      last.close = b.close; last.date = b.date; last.volume = (last.volume || 0) + (b.volume || 0);
    } else out.push({ ...b, _k: k } as any);
  }
  return out;
}

/* ── السيولة اللحظية (Smart Money) بعتبات المستثمر ─────────────────────── */
export function liquidity(bars: VBar[], volLen = 20, trader = false) {
  const vols = bars.map(b => b.volume || 0);
  const hasVol = vols.some(v => v > 0);
  const i = bars.length - 1;
  if (!hasVol || i < volLen) return { state: "—", color: "muted", rvol: null as number | null, dry: false, squeeze: false, accum: false, dump: false, dist: false };
  const avg = sma(vols, volLen)[i] || 1;
  const rvol = (vols[i] / avg) * 100;
  const spreads = bars.map(b => b.high - b.low);
  const avgSp = sma(spreads, volLen)[i] || 0;
  const b = bars[i], sp = b.high - b.low, pos = sp === 0 ? 0.5 : (b.close - b.low) / sp;
  const T = trader ? [150, 120, 150, 120, 80] : [200, 160, 200, 160, 60];
  const squeeze = rvol > T[0] && pos > 0.7 && b.close > b.open;
  const accum = rvol > T[1] && sp < avgSp && pos > 0.5;
  const dump = rvol > T[2] && pos < 0.3 && b.close < b.open;
  const dist = rvol > T[3] && sp < avgSp && pos < 0.5;
  const dry = rvol < T[4];
  const [state, color] = squeeze ? ["اندفاع شرائي", "pos"] : accum ? ["تجميع خفي", "pos"] : dump ? ["انهيار بيعي", "neg"]
    : dist ? ["تصريف بيعي", "neg"] : dry ? ["جفاف سيولة", "muted"] : ["محايد", "warn"];
  return { state, color, rvol, dry, squeeze, accum, dump, dist };
}

/* ── MACD الذكي (المحلّل) ─────────────────────────────────────────────── */
export function macdSmart(bars: Bar[], fast = 12, slow = 26, sig = 9, sens = 0.25) {
  const c = bars.map(b => b.close);
  const f = ema(c, fast), s = ema(c, slow);
  const line = c.map((_, i) => f[i] == null || s[i] == null ? null : f[i]! - s[i]!);
  const valid = line.map(v => v ?? 0);
  const firstIdx = line.findIndex(v => v != null);
  const sigRaw = ema(valid.slice(firstIdx < 0 ? 0 : firstIdx), sig);
  const signal = line.map((_, i) => i < firstIdx ? null : sigRaw[i - firstIdx]);
  const hist = line.map((v, i) => v == null || signal[i] == null ? null : v - signal[i]!);
  const i = bars.length - 1;
  const L = line[i], S = signal[i], H = hist[i], H1 = hist[i - 1];
  if (L == null || S == null || H == null || H1 == null) return null;
  const a = atr(bars, 14)[i];
  const mAbs = Math.abs(H), zero = 0.05 * a;
  const side = Math.abs(L) < zero && Math.abs(S) < zero && mAbs < 0.1 * a;
  const L1 = line[i - 1]!, S1 = signal[i - 1]!;
  const crossUp = L1 <= S1 && L > S, crossDn = L1 >= S1 && L < S;
  const mState = Math.abs(H) > Math.abs(H1) ? "تسارع" : Math.abs(H) < Math.abs(H1) ? "تباطؤ" : "ثبات";
  const mStr = mAbs < 0.1 * a ? "منخفض" : mAbs < sens * a ? "متوسط" : "مرتفع";
  const reading = side ? `جانبي / تثبيت / الزخم ${mStr}`
    : L > S ? (L > 0 ? (crossUp ? "صاعد قوي / تقاطع فوق الصفر" : `سيطرة شرائية / ${mState} ${mStr}`)
                     : (crossUp ? "اختراق صعودي / تقاطع تحت الصفر" : `صاعد ضعيف / ارتداد / ${mState}`))
            : (L < 0 ? (crossDn ? "هابط قوي / تقاطع تحت الصفر" : `سيطرة بيعية / ${mState} ${mStr}`)
                     : (crossDn ? "اختراق هبوطي / تقاطع فوق الصفر" : `هابط ضعيف / تصحيح / ${mState}`));
  const summary = side ? "عرضي" : L > S && L > 0 ? "صعود" : L < S && L < 0 ? "هبوط" : "عرضي";
  const b = bars[i], b1 = bars[i - 1];
  const div = b.high > b1.high && L < L1 && L > 0 ? "تحذير: انعكاس مرتقب / بيع"
    : b.low < b1.low && L > L1 && L < 0 ? "تحذير: انعكاس مرتقب / شراء" : "لا يوجد انعكاس حالي";
  return { reading, summary, divergence: div, readingTone: side ? "warn" : L > S ? "pos" : "neg", hist };
}

/* ══ الترند التلقائي — ترجمةٌ حرفيّة لـ ZZ و Pointer و Correction_Checker ══ */
export type TLine = { x1: number; y1: number; x2: number; y2: number; major: boolean; up: boolean };
export type TSignal = { index: number; kind: "breakDown" | "reactUp" | "breakUp" | "reactDown" };

function pivotAt(bars: Bar[], c: number, pp: number, high: boolean): boolean {
  if (c - pp < 0 || c + pp >= bars.length) return false;
  const v = high ? bars[c].high : bars[c].low;
  for (let k = c - pp; k <= c + pp; k++) {
    if (k === c) continue;
    const w = high ? bars[k].high : bars[k].low;
    if (high ? (k < c ? w >= v : w > v) : (k < c ? w <= v : w < v)) return false;
  }
  return true;
}

export function autoTrend(bars: Bar[], PP = 15): { lines: TLine[]; signals: TSignal[] } {
  const n = bars.length;
  const T: string[] = [], V: number[] = [], I: number[] = [];
  const TA: string[] = [], VA: number[] = [], IA: number[] = [];
  let HighValue = NaN, LowValue = NaN, HighIndex = 0, LowIndex = 0;
  let MjH = NaN, MjL = NaN;
  let lock0 = true, lock1 = true;
  let prevLastV: number | undefined, prevLastT: string | undefined;
  let x0 = 0, y0 = 0, t0 = "", prevT0 = "";
  const types = ["MHL", "MLH", "MHH", "MLL", "mHL", "mLH", "mHH", "mLL"];
  const ptr: Record<string, { X0: number; Y0: number; X1: number; Y1: number }> = {};
  types.forEach(t => ptr[t] = { X0: 0, Y0: 0, X1: 0, Y1: 0 });
  const prevX0: Record<string, number> = {};
  // مدقّقو الخطوط الثمانية: [نوعُ المؤشّر، اتجاهُ الخطّ، رئيسيّ؟]
  const checkers: [string, "Up" | "Down", boolean][] = [
    ["MLL", "Up", true], ["MHH", "Down", true], ["MHL", "Up", true], ["MLH", "Down", true],
    ["mLL", "Up", false], ["mHH", "Down", false], ["mHL", "Up", false], ["mLH", "Down", false]];
  const st = checkers.map(() => ({ line: null as null | { x1: number; y1: number; x2: number; y2: number; slope: number },
    permitSet: true, prevPermitSet: true }));
  const signals: TSignal[] = [];
  const push = (t: string, v: number, i: number) => { T.push(t); V.push(v); I.push(i); };
  const pop = () => { T.pop(); V.pop(); I.pop(); };
  const lastT = () => T[T.length - 1], lastV = () => V[V.length - 1];
  const hType = () => T.length > 2 ? (V[V.length - 2] < HighValue ? "HH" : "LH") : "H";
  const lType = () => T.length > 2 ? (V[V.length - 2] < LowValue ? "HL" : "LL") : "L";

  for (let t = 0; t < n; t++) {
    const c = t - PP;
    const hp = c >= 0 && pivotAt(bars, c, PP, true), lp = c >= 0 && pivotAt(bars, c, PP, false);
    if (hp) { HighValue = bars[c].high; HighIndex = c; }
    if (lp) { LowValue = bars[c].low; LowIndex = c; }
    const close = bars[t].close;
    const HP = HighValue, LP = LowValue;
    if (hp && lp) {
      if (T.length >= 1) {
        const lt = lastT();
        if (lt === "L" || lt === "LL") {
          if (LP < lastV()) { pop(); push(lType(), LowValue, LowIndex); }
          else push(hType(), HighValue, HighIndex);
        } else if (lt === "H" || lt === "HH") {
          if (HP > lastV()) { pop(); push(hType(), HighValue, HighIndex); }
          else push(lType(), LowValue, LowIndex);
        } else if (lt === "LH") {
          if (HP < lastV()) push(lType(), LowValue, LowIndex);
          else if (HP > lastV()) {
            if (close < lastV()) { pop(); push(hType(), HighValue, HighIndex); }
            else if (close > lastV()) push(lType(), LowValue, LowIndex);
          }
        } else if (lt === "HL") {
          if (LP > lastV()) push(hType(), HighValue, HighIndex);
          else if (LP < lastV()) {
            if (close > lastV()) { pop(); push(lType(), LowValue, LowIndex); }
            else if (close < lastV()) push(hType(), HighValue, HighIndex);
          }
        }
      }
    } else if (hp) {
      if (T.length === 0) { T.unshift("H"); V.unshift(HighValue); I.unshift(HighIndex); }
      else {
        const lt = lastT();
        if (lt === "L" || lt === "HL" || lt === "LL") {
          if (HP > lastV()) push(hType(), HighValue, HighIndex);
          else if (HP < lastV()) { pop(); push(lType(), LowValue, LowIndex); }
        } else if (lt === "H" || lt === "HH" || lt === "LH") {
          if (lastV() < HighValue) { pop(); push(hType(), HighValue, HighIndex); }
        }
      }
    } else if (lp) {
      if (T.length === 0) { T.unshift("L"); V.unshift(LowValue); I.unshift(LowIndex); }
      else {
        const lt = lastT();
        if (lt === "H" || lt === "HH" || lt === "LH") {
          if (LP < lastV()) push(lType(), LowValue, LowIndex);
          else if (LP > lastV()) { pop(); push(hType(), HighValue, HighIndex); }
        } else if (lt === "L" || lt === "HL" || lt === "LL") {
          if (lastV() > LowValue) { pop(); push(lType(), LowValue, LowIndex); }
        }
      }
    }
    // المستويان الرئيسيّان الأوّلان
    if (T.length === 2) {
      if (T[0] === "H") { MjH = V[0]; MjL = V[1]; } else if (T[0] === "L") { MjH = V[1]; MjL = V[0]; }
    }
    if (V.length === 1 && lock0) { TA.unshift("M" + T[0]); VA.unshift(V[0]); IA.unshift(I[0]); lock0 = false; }
    if (V.length === 2 && lock1) { TA.splice(1, 0, "M" + T[1]); VA.splice(1, 0, V[1]); IA.splice(1, 0, I[1]); lock1 = false; }
    if (V.length > 1) {
      const lv = lastV(), ltp = lastT();
      if (prevLastV !== undefined && prevLastV !== lv) {
        const prevDir = prevLastT ? prevLastT.slice(-1) : "", curDir = ltp.slice(-1);
        if (prevDir !== curDir) { TA.push("m" + ltp); VA.push(lv); IA.push(I[I.length - 1]); }
        else { VA.pop(); IA.pop(); VA.push(lv); IA.push(I[I.length - 1]); }
      }
    }
    prevLastV = V.length ? lastV() : undefined; prevLastT = T.length ? lastT() : undefined;
    if (VA.length > 1) {
      const la = () => TA[TA.length - 1], la2 = () => TA[TA.length - 2];
      const setLast = (v: string) => { TA[TA.length - 1] = v; };
      if (close > MjH) {
        if (la() === "mL") { setLast("ML"); MjL = VA[VA.length - 1]; }
        else if (la() === "mHL" || la() === "mLL") { setLast("M" + lastT()); MjL = VA[VA.length - 1]; }
        else if (["mLH", "mHH", "MLH", "MHH"].includes(la())) {
          if (la2() === "mHL" || la2() === "mLL") { TA[TA.length - 2] = "M" + T[T.length - 2]; MjL = VA[VA.length - 2]; }
        }
      }
      if (VA[VA.length - 1] > MjH) {
        if (la() === "mH") { setLast("MH"); MjH = VA[VA.length - 1]; }
        else if (["mLH", "mHH", "MHH"].includes(la())) { setLast("M" + lastT()); MjH = VA[VA.length - 1]; }
      }
      if (close < MjL) {
        if (["mH", "mLH", "mHH"].includes(la())) { setLast("M" + lastT()); MjH = VA[VA.length - 1]; }
        else if (["mHL", "mLL", "MLL"].includes(la())) {
          if (la2() === "mLH" || la2() === "mHH") { TA[TA.length - 2] = "M" + T[T.length - 2]; MjH = VA[VA.length - 2]; }
        }
      }
      if (VA[VA.length - 1] < MjL) {
        if (la() === "mL") { setLast("ML"); MjL = VA[VA.length - 1]; }
        else if (["mHL", "mLL", "MLL"].includes(la())) { setLast("M" + lastT()); MjL = VA[VA.length - 1]; }
      }
    }
    // المؤشّر العامّ ثمّ مؤشّراتُ الأنواع
    prevT0 = t0;
    if (TA.length > 2) { x0 = IA[IA.length - 1]; y0 = VA[VA.length - 1]; t0 = TA[TA.length - 1]; }
    for (const ty of types) {
      const p = ptr[ty];
      prevX0[ty] = p.X0;
      if (t0 !== prevT0 && t0 === ty) {
        if (p.X0 === 0) { p.X0 = x0; p.Y0 = y0; }
        else if (p.X1 === 0) { p.X1 = x0; p.Y1 = y0; }
        else { p.X0 = p.X1; p.Y0 = p.Y1; p.X1 = x0; p.Y1 = y0; }
      }
    }
    // مدقّقُ التصحيح لكلّ خطّ
    checkers.forEach(([ty, dir, major], k) => {
      const p = ptr[ty], s = st[k];
      if (p.X0 !== 0 && p.X1 !== 0 && p.X0 !== prevX0[ty]) {
        if (dir === "Up" ? p.Y1 > p.Y0 : p.Y1 < p.Y0) {
          const slope = (p.Y1 - p.Y0) / (p.X1 - p.X0);
          let permit = true;
          for (let j = 1; j <= t - p.X0; j++) {
            const x = p.X0 + j, lp2 = p.Y0 + slope * j, cl = bars[x].close;
            // نقطةُ الارتكاز الثانية يمرّ بها الخطّ بناءً؛ وعلى شموعٍ بلا ذيول (تاسي اليومي) إغلاقُها = قمّتُها
            if (x === p.X1) continue;
            permit = (dir === "Up" ? cl > lp2 : cl < lp2) && permit;
          }
          if (permit) { s.line = { x1: p.X0, y1: p.Y0, x2: p.X1, y2: p.Y1, slope }; s.permitSet = true; }
        }
      }
      if (s.line) {
        const at = (x: number) => s.line!.y1 + s.line!.slope * (x - s.line!.x1);
        const prevPS = s.permitSet;
        if ((dir === "Up" ? close > at(t) : close < at(t)) && s.permitSet) {
          s.line.x2 = Math.min(t + 1, n - 1); s.line.y2 = at(s.line.x2);
        } else s.permitSet = false;
        const brk = prevPS && !s.permitSet;
        const b = bars[t];
        const react = s.permitSet && (dir === "Up" ? (close > at(t) && b.low < at(t)) : (close < at(t) && b.high > at(t)));
        if (brk) signals.push({ index: t, kind: dir === "Up" ? "breakDown" : "breakUp" });
        if (react) signals.push({ index: t, kind: dir === "Up" ? "reactUp" : "reactDown" });
      }
      void major;
    });
  }
  const lines = st.map((s, k) => s.line ? { x1: s.line.x1, y1: s.line.y1, x2: s.line.x2, y2: s.line.y2,
    major: checkers[k][2], up: checkers[k][1] === "Up" } : null).filter(Boolean) as TLine[];
  return { lines, signals };
}

/* ══ لوحةُ ملخّص اتجاه السوق (المستثمر) على الإطارات المتاحة من شموعٍ يومية ══
 * السكربت للمستثمر: يوميٌّ EMA200 (4) · 4H VWAP (3) · 1H VWAP (2) · 15M VWAP (1).
 * ولا شموعَ لحظيةً عندنا، فتُستعمل الإطاراتُ المحسوبةُ من اليوميّ نفسِه:
 * يوميٌّ EMA200 (4) · شهريٌّ VWAP (3) · أسبوعيٌّ VWAP (2) — ويُذكر ذلك في اللوحة. */
export type Dash = {
  rows: { tf: string; up: boolean | null }[]; score: number; liq: ReturnType<typeof liquidity>;
  trend: { state: string; tone: string; adx: number | null }; decision: string; tone: string;
  power: number; trust: number; vixWarn: string | null; newsWarn: boolean; summary: string;
};

export function dashboard(bars: VBar[], opts: { bull?: number; bear?: number; vix?: number | null;
  vixWarn?: number; vixBlock?: number; newsDates?: string[]; today?: string } = {}): Dash | null {
  if (bars.length < 30) return null;
  const c = bars.map(b => b.close), i = bars.length - 1;
  const e200 = ema(c, Math.min(200, bars.length - 1));
  const upD = e200[i] == null ? null : c[i] > e200[i]!;
  const vwM = vwapAnchored(bars, "Month").vwap[i], vwW = vwapAnchored(bars, "Week").vwap[i];
  const upM = c[i] > vwM, upW = c[i] > vwW;
  const score = (upD ? 4 : -4) + (upM ? 3 : -3) + (upW ? 2 : -2);
  const bull = opts.bull ?? 5, bear = opts.bear ?? -5;           // 6/−6 من 10 ⇒ 5/−5 من 9
  const { plus, minus, adx } = dmi(bars, 14, 14);
  const A = adx[i], P = plus[i], M = minus[i];
  const vols = bars.map(b => b.volume || 0), avgV = sma(vols, 20);
  const volAccum3 = [0, 1, 2].every(k => avgV[i - k] != null && vols[i - k] > avgV[i - k]!);
  const e200Rising = e200[i] != null && e200[i - 1] != null && e200[i]! > e200[i - 1]!;
  const adxWeak = A == null ? true : (A < 20 && !(e200Rising || volAccum3));
  const tUp = !adxWeak && (P ?? 0) > (M ?? 0), tDn = !adxWeak && (M ?? 0) > (P ?? 0);
  const trend = adxWeak ? { state: "ضعيف", tone: "warn", adx: A } : tUp ? { state: "صاعد", tone: "pos", adx: A }
    : { state: "هابط", tone: "neg", adx: A };
  const liq = liquidity(bars, 20, false);
  const hi1 = i > 0 ? bars[i - 1].high : bars[i].high, lo1 = i > 0 ? bars[i - 1].low : bars[i].low;
  const trustBull = (upW ? 2 : 0) + (upM ? 2 : 0) + (e200Rising ? 3 : 0) + (volAccum3 ? 2 : 0) + (c[i] > hi1 ? 1 : 0);
  const trustBear = (!upW ? 2 : 0) + (!upM ? 2 : 0) + (!e200Rising ? 3 : 0) + (volAccum3 ? 2 : 0) + (c[i] < lo1 ? 1 : 0);
  // القرارُ الخامُ على كلّ شمعةٍ للذاكرة (تأكيدُ شمعتين)
  const rawAt = (j: number): [string, number] => {
    const cj = c[j], ej = e200[j]; if (ej == null) return ["انتظار", 0];
    const uD = cj > ej, uM = cj > vwapAnchored(bars.slice(0, j + 1), "Month").vwap[j];
    const Aj = adx[j], Pj = plus[j] ?? 0, Mj = minus[j] ?? 0;
    const eR = e200[j - 1] != null && ej > e200[j - 1]!;
    const weak = Aj == null ? true : (Aj < 20 && !eR);
    const dry = liquidity(bars.slice(0, j + 1), 20, false).dry;
    if (weak || dry) return ["انتظار", 0];
    if (uD && uM && Pj > Mj) return ["صعود", j === i ? trustBull : 0];
    if (!uD && !uM && Mj > Pj) return ["هبوط", j === i ? trustBear : 0];
    return ["محايد", 0];
  };
  let stable = "انتظار", pending = "", pend = 0, trust = 0;
  for (let j = Math.max(0, i - 60); j <= i; j++) {
    const [d, tr] = rawAt(j);
    if (d === stable) { pending = ""; pend = 0; trust = tr; }
    else if (d === pending) { pend++; if (pend >= 2) { stable = d; trust = tr; pending = ""; pend = 0; } }
    else { pending = d; pend = 1; }
  }
  let decision = stable, tone = stable === "صعود" ? "pos" : stable === "هبوط" ? "neg" : stable === "محايد" ? "warn" : "muted";
  let vixWarn: string | null = null;
  const vix = opts.vix;
  if (vix != null && vix > (opts.vixWarn ?? 25)) {
    vixWarn = `⚠ VIX ${Math.round(vix)}`;
    if (vix > (opts.vixBlock ?? 35)) { decision = "خروج"; tone = "neg"; trust = 0; }
  }
  const newsWarn = !!(opts.today && (opts.newsDates || []).includes(opts.today));
  const summary = score >= bull ? "صعود" : score <= bear ? "هبوط" : "محايد";
  return { rows: [{ tf: "يومي · EMA200", up: upD }, { tf: "شهري · VWAP", up: upM }, { tf: "أسبوعي · VWAP", up: upW }],
    score, liq, trend, decision, tone, power: Math.min(Math.abs(score), 10), trust: Math.min(trust, 10), vixWarn, newsWarn, summary };
}

/** شريطُ السكربت البصريّ █░ من 0 إلى 10 */
export const bar10 = (v: number) => { const f = Math.min(Math.round(Math.abs(v)), 10); return "█".repeat(f) + "░".repeat(10 - f); };

/* ── أداةُ الصفقة (Goldman Mode) على شموعٍ يومية ─────────────────────────── */
export function tradeTool(bars: Bar[], vix: number | null, newsDay: boolean) {
  const i = bars.length - 1; if (i < 2) return null;
  const b = bars[i], p = bars[i - 1];
  const pdh = p.high, pdl = p.low;
  const gap = p.close ? (b.open - p.close) / p.close * 100 : 0;
  let s = 0;
  if (vix != null) { if (vix > 25) s -= 2; else if (vix < 15) s += 1; }
  if (Math.abs(gap) > 0.5) s += gap > 0 ? 2 : -2; else if (Math.abs(gap) > 0.2) s += gap > 0 ? 1 : -1;
  if (b.close > pdh) s += 2; else if (b.close < pdl) s -= 2;
  else { const pos = (b.close - pdl) / Math.max(pdh - pdl, 0.01); if (pos > 0.65) s += 0.5; else if (pos < 0.35) s -= 0.5; }
  const dec = newsDay ? "⚠ خبر" : (vix != null && vix > 35) ? "خروج" : s >= 3 ? "CALL ✅" : s <= -3 ? "PUT ✅"
    : (vix != null && vix > 25) ? "انتظار" : "محايد";
  const call = dec.includes("CALL"), put = dec.includes("PUT") && !call;
  const rng = Math.max(pdh - pdl, 4);
  const strike = call ? Math.ceil(b.close / 5) * 5 : put ? Math.floor(b.close / 5) * 5 : 0;
  const target = call ? Math.min(pdh, b.close + rng * 0.5) : put ? Math.max(pdl, b.close - rng * 0.5) : 0;
  const stop = call ? Math.max(pdl, b.close - rng * 0.3) : put ? Math.min(pdh, b.close + rng * 0.3) : 0;
  const rr = Math.abs(target - b.close) / Math.max(Math.abs(b.close - stop), 0.01);
  return { dec, call, put, strike, target, stop, rr, gap, conf: Math.min(Math.abs(s) / 6 * 10, 10),
    entry: "انتظر الغد" /* على الشموع اليومية لا جلسةَ لحظية — كما يُخرجها السكربت */ };
}

/* ── إعداداتُ المؤشّر الافتراضية (قيمُ السكربت) ─────────────────────────── */
export const D7M_DEFAULTS = {
  fib: true, fibDev: 3, fibDepth: 7, fibReverse: false, fibZones: true,
  fibLevels: Object.fromEntries(FIB_LEVELS.map(([lv]) => [String(lv), true])) as Record<string, boolean>,
  trend: true, trendPP: 15, trendShapes: false,
  channel: true, chDev: 3, chDepth: 20,
  vwap: true, vwapAnchor: "Session" as "Session" | "Week" | "Month" | "Year", vwapBand: false, vwapMult: 1,
  ema20: false, ema50: false, ema100: false, ema200: false, ema400: false,
  pdh: false, pdl: false, pdc: false, dOpen: false,
  dashboard: true, bull: 5, bear: -5,
  macdDash: false, alertsDash: false, tradeTool: false,
  vixWarn: 25, vixBlock: 35, news: false,
  newsDates: "2026-01-28, 2026-03-18, 2026-04-29, 2026-06-17, 2026-07-29, 2026-09-16, 2026-10-28, 2026-12-09, 2026-01-13, 2026-02-11, 2026-03-11, 2026-04-10, 2026-05-12, 2026-06-10, 2026-07-14, 2026-08-12, 2026-09-11, 2026-10-14, 2026-11-10, 2026-12-10",
};
export type D7MSettings = typeof D7M_DEFAULTS;
