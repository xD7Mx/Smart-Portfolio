/* نافذةُ إعدادات المؤشّر كتريدنق فيو (‏D744 · المالك 2026-11-15: «المؤشّراتُ قابلةٌ للتعديل — 14 3 3 · 8 8 3 — مثل تريدنق فيو»):
   «المدخلات» و«النمط»، وكلُّ رقمٍ يُكتب ويُطبَّق فوراً حين يصحّ، و«الافتراضي» يعيد قيمَ السكربت. بلغة نافذة D7M نفسِها.
   ‏D784 (المالك 2026-11-22): «إعداداتُ ستوكاستيك RSI غيرُ ناضجة — يجب أن تكون ناضجةً ممتازة: أغيّر الألوان، أغيّر الرسم» — فنمطُه كتريدنق فيو:
   خطّا ‏K و‏D (إظهارٌ ولونٌ وسُمكٌ ونوعُ خطّ)، والحدودُ الثلاثة (قيمٌ وإظهارٌ ولونٌ ونوع)، والخلفيةُ بينها (إظهارٌ ولونٌ وشفافية). */
import { useEffect, useState } from "react";
import Toggle from "../common/Toggle";
import { CVD_DEFAULTS, CvdCfg, STOCHRSI_DEFAULTS, StochRsiCfg, SrcKey, LineSt } from "../../lib/indicators";

/** لونُ الرمز الحاليّ بصيغة ‏#rrggbb ليظهر في منتقي اللون — اللونُ المرسومُ فعلاً حين لم يختر المالكُ غيرَه */
function tokenHex(name: string): string {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  if (/^#[0-9a-f]{6}$/i.test(v)) return v;
  if (/^#[0-9a-f]{3}$/i.test(v)) return "#" + v.slice(1).split("").map(c => c + c).join("");
  const m = v.match(/\d+(\.\d+)?/g);
  return m && m.length >= 3 ? "#" + m.slice(0, 3).map(n => Math.round(+n).toString(16).padStart(2, "0")).join("") : "#000000";
}
function Color({ label, value, token, onChange }: { label: string; value: string; token: string; onChange: (v: string) => void }) {
  return (
    <label className="d7m-row">
      <span>{label}</span>
      <span className="flex items-center gap-1">
        <input type="color" aria-label={label} value={value || tokenHex(token)} onChange={e => onChange(e.target.value)} />
        {value && <button type="button" className="d7m-reset" title="لونُ المظهر" aria-label={`إرجاع ${label}`} onClick={() => onChange("")}>↺</button>}
      </span>
    </label>
  );
}
const STYLES: [LineSt, string][] = [["solid", "متّصل"], ["dashed", "متقطّع"], ["dotted", "منقّط"]];
const WIDTHS: ["1" | "2" | "3" | "4", string][] = [["1", "1"], ["2", "2"], ["3", "3"], ["4", "4"]];

function Num({ label, value, min = 1, max = 500, onChange, bare }: { label: string; value: number; min?: number; max?: number; onChange: (v: number) => void; bare?: boolean }) {
  const [txt, setTxt] = useState(String(value));
  useEffect(() => { setTxt(String(value)); }, [value]);
  const commit = (t: string) => { const v = Math.floor(Number(t.replace(/[٠-٩]/g, d => String(d.charCodeAt(0) - 0x0660)))); if (Number.isFinite(v) && v >= min && v <= max) onChange(v); };
  const input = <input type="text" inputMode="numeric" lang="en" dir="ltr" value={txt} aria-label={label}
    onChange={e => { setTxt(e.target.value); commit(e.target.value); }} onBlur={() => setTxt(String(value))} />;
  if (bare) return input;
  return (
    <label className="d7m-row">
      <span>{label}</span>
      {input}
    </label>
  );
}
function Seg<T extends string>({ label, value, opts, onChange }: { label: string; value: T; opts: [T, string][]; onChange: (v: T) => void }) {
  return (
    <div className="d7m-row d7m-col">
      <span>{label}</span>
      <span className="seg inline-flex flex-wrap">
        {opts.map(([v, t]) => (
          <button key={v} type="button" className={"seg-btn chip" + (value === v ? " on" : "")} aria-pressed={value === v} onClick={() => onChange(v)}>{t}</button>
        ))}
      </span>
    </div>
  );
}
const SRC: [SrcKey, string][] = [["close", "close"], ["open", "open"], ["high", "high"], ["low", "low"], ["hl2", "hl2"], ["hlc3", "hlc3"], ["ohlc4", "ohlc4"]];

export default function IndSettings({ kind, sr, cvd, onSr, onCvd, onClose }: {
  kind: "stochrsi" | "cvd"; sr: StochRsiCfg; cvd: CvdCfg; onSr: (p: Partial<StochRsiCfg>) => void; onCvd: (p: Partial<CvdCfg>) => void; onClose: () => void;
}) {
  const title = kind === "stochrsi" ? "Stoch RSI" : "CVD D7M";
  return (
    <div className="d7m-modal" role="dialog" aria-label={`إعدادات ${title}`} onClick={onClose} data-role="ind-settings">
      <div className="d7m-sheet" onClick={e => e.stopPropagation()}>
        <div className="d7m-head">
          <strong dir="ltr">{title}</strong>
          <button type="button" className="d7m-btn" data-role="ind-reset"
            onClick={() => (kind === "stochrsi" ? onSr({ ...STOCHRSI_DEFAULTS }) : onCvd({ ...CVD_DEFAULTS }))}>الافتراضي</button>
          <button type="button" className="d7m-btn" onClick={onClose} aria-label="إغلاق">✕</button>
        </div>
        {kind === "stochrsi" ? (
          <div>
            <fieldset><legend>المدخلات</legend>
              <Num label="K" value={sr.k} onChange={v => onSr({ k: v })} />
              <Num label="D" value={sr.d} onChange={v => onSr({ d: v })} />
              <Num label="طولُ RSI" value={sr.rsiLen} onChange={v => onSr({ rsiLen: v })} />
              <Num label="طولُ الستوكاستيك" value={sr.stochLen} onChange={v => onSr({ stochLen: v })} />
              <Seg label="مصدرُ RSI" value={sr.src} opts={SRC} onChange={v => onSr({ src: v })} />
            </fieldset>
            {([["k", "خطّ K", "--info-ink"], ["d", "خطّ D", "--gauge-warn"]] as const).map(([x, name, tk]) => (
              <fieldset key={x} data-role={`sr-${x}`}><legend dir="auto">{name}</legend>
                <div className="d7m-row"><Toggle checked={sr[`${x}On`] !== false} onChange={v => onSr({ [`${x}On`]: v } as Partial<StochRsiCfg>)} label="إظهار" /></div>
                <Color label="اللون" value={sr[`${x}Color`] || ""} token={tk} onChange={v => onSr({ [`${x}Color`]: v } as Partial<StochRsiCfg>)} />
                <Seg label="السُّمك" value={String(sr[`${x}Width`] || 1) as "1"} opts={WIDTHS} onChange={v => onSr({ [`${x}Width`]: Number(v) } as Partial<StochRsiCfg>)} />
                <Seg label="نوعُ الخطّ" value={sr[`${x}Style`] || "solid"} opts={STYLES} onChange={v => onSr({ [`${x}Style`]: v } as Partial<StochRsiCfg>)} />
              </fieldset>
            ))}
            <fieldset data-role="sr-bands"><legend>الحدود</legend>
              {/* كلُّ حدٍّ صفٌّ واحد: إظهارُه وقيمتُه معاً */}
              {([["upOn", "upper", "العلويّ"], ["midOn", "middle", "الأوسط"], ["loOn", "lower", "السفليّ"]] as const).map(([on, key, nm]) => (
                <div key={key} className="d7m-row sr-band" data-band={key}>
                  <Toggle checked={sr[on] !== false} onChange={v => onSr({ [on]: v } as Partial<StochRsiCfg>)} label={`الحدُّ ${nm}`} />
                  <Num bare label={`قيمةُ ${nm}`} value={sr[key]} min={0} max={100} onChange={v => onSr({ [key]: v } as Partial<StochRsiCfg>)} />
                </div>
              ))}
              <Color label="لونُ الحدود" value={sr.bandColor || ""} token="--ink-muted" onChange={v => onSr({ bandColor: v })} />
              <Seg label="نوعُ خطّ الحدود" value={sr.bandStyle || "dashed"} opts={STYLES} onChange={v => onSr({ bandStyle: v })} />
            </fieldset>
            <fieldset data-role="sr-bg"><legend>الخلفية</legend>
              <div className="d7m-row"><Toggle checked={sr.bgOn !== false} onChange={v => onSr({ bgOn: v })} label="إظهارُ الخلفية بين الحدّين" /></div>
              <Color label="لونُها" value={sr.bgColor || ""} token="--info-ink" onChange={v => onSr({ bgColor: v })} />
              <Num label="الشفافية ٪" value={Number(sr.bgOpacity ?? 10)} min={0} max={100} onChange={v => onSr({ bgOpacity: v })} />
            </fieldset>
          </div>
        ) : (
          <div>
            <fieldset><legend>المدخلات</legend>
              <Seg label="النمط" value={cvd.style} opts={[["candle", "شموع"], ["line", "خطّ"]]} onChange={v => onCvd({ style: v })} />
              <Seg label="المقياس" value={cvd.scale} opts={[["levels", "مستويات"], ["pct", "نسبة"], ["volume", "احجام"]]} onChange={v => onCvd({ scale: v })} />
              <Num label="الفترة" value={cvd.len} min={10} max={1000} onChange={v => onCvd({ len: v })} />
              <div className="d7m-row"><Toggle checked={cvd.ha} onChange={v => onCvd({ ha: v })} label="شموع هايكن آشي" /></div>
            </fieldset>
            <fieldset><legend>المتوسّطات</legend>
              {(["ema1", "ema2", "sma1", "sma2"] as const).map(k => (
                <div key={k} className="ind-ma">
                  <div className="d7m-row"><Toggle checked={!!cvd[k]} onChange={v => onCvd({ [k]: v } as Partial<CvdCfg>)} label={`${k.startsWith("ema") ? "EMA" : "SMA"} ${k.endsWith("1") ? "الأوّل" : "الثاني"}`} /></div>
                  <Num label="الطول" value={cvd[`${k}Len` as "ema1Len"]} onChange={v => onCvd({ [`${k}Len`]: v } as Partial<CvdCfg>)} />
                </div>
              ))}
            </fieldset>
          </div>
        )}
      </div>
    </div>
  );
}
