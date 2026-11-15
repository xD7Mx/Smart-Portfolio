/* نافذةُ إعدادات المؤشّر كتريدنق فيو (‏D744 · المالك 2026-11-15: «المؤشّراتُ قابلةٌ للتعديل — 14 3 3 · 8 8 3 — مثل تريدنق فيو»):
   «المدخلات» و«النمط»، وكلُّ رقمٍ يُكتب ويُطبَّق فوراً حين يصحّ، و«الافتراضي» يعيد قيمَ السكربت. بلغة نافذة D7M نفسِها. */
import { useEffect, useState } from "react";
import Toggle from "../common/Toggle";
import { CVD_DEFAULTS, CvdCfg, STOCHRSI_DEFAULTS, StochRsiCfg, SrcKey } from "../../lib/indicators";

function Num({ label, value, min = 1, max = 500, onChange }: { label: string; value: number; min?: number; max?: number; onChange: (v: number) => void }) {
  const [txt, setTxt] = useState(String(value));
  useEffect(() => { setTxt(String(value)); }, [value]);
  const commit = (t: string) => { const v = Math.floor(Number(t.replace(/[٠-٩]/g, d => String(d.charCodeAt(0) - 0x0660)))); if (Number.isFinite(v) && v >= min && v <= max) onChange(v); };
  return (
    <label className="d7m-row">
      <span>{label}</span>
      <input type="text" inputMode="numeric" lang="en" dir="ltr" value={txt} aria-label={label}
        onChange={e => { setTxt(e.target.value); commit(e.target.value); }} onBlur={() => setTxt(String(value))} />
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
            <fieldset><legend>النمط</legend>
              <Num label="الحدُّ العلويّ" value={sr.upper} min={0} max={100} onChange={v => onSr({ upper: v })} />
              <Num label="الحدُّ الأوسط" value={sr.middle} min={0} max={100} onChange={v => onSr({ middle: v })} />
              <Num label="الحدُّ السفليّ" value={sr.lower} min={0} max={100} onChange={v => onSr({ lower: v })} />
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
