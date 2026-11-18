/* ══ مبدّلُ سوق صقر ══ (‏D764 بأمر المالك 2026-11-18)
   «نخلّي صقر للسوق السعوديّ وللسوق الأمريكيّ — ولكلٍّ منهما استراتيجيتُه». فمبدّلٌ واحدٌ أعلى المحفظة ولوحةِ صقر، يُحفظ اختيارُه. */
import type { Market } from "./saqr";

export default function MarketSwitch({ value, onChange }: { value: Market; onChange: (m: Market) => void }) {
  return (
    <div className="seg inline-flex sq-mkt" role="tablist" aria-label="سوقُ صقر" data-role="sq-market">
      {([["us", "السوق الأمريكيّ"], ["sa", "السوق السعوديّ"]] as const).map(([k, t]) => (
        <button key={k} type="button" role="tab" aria-selected={value === k} className={"seg-btn chip" + (value === k ? " on" : "")}
          onClick={() => onChange(k)} data-market={k}>{t}</button>
      ))}
    </div>
  );
}
