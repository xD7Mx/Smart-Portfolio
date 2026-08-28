import React, { useEffect, useRef } from "react";

/**
 * TradingView Advanced Chart — full pro charting embedded in the app.
 * The user can add their own indicators, drawings, timeframes and change the
 * symbol from inside the widget (just like TradingView). Saudi tickers are
 * mapped to the Tadawul exchange (e.g. 2222 → TADAWL:2222).
 */
export function toTvSymbol(input: string): string {
  const s = (input || "").trim().toUpperCase();
  if (!s) return "TADAWL:2222";
  // TASI index — also accept the Yahoo-style spellings used internally
  // elsewhere in the app (^TASI.SR / ^TASI / TASI.SR), not just "TASI".
  if (s === "TASI" || s === "^TASI" || s === "^TASI.SR" || s === "TASI.SR") return "TADAWL:TASI";
  if (/^\d{3,4}$/.test(s)) return `TADAWL:${s}`;      // Saudi listed company
  if (s.includes(":")) return s;                       // already exchange-qualified
  return s;                                            // e.g. AAPL / BTCUSD
}

export default function TradingViewChart({ symbol, theme = "dark" }: { symbol: string; theme?: "dark" | "light" }) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    el.innerHTML = "";
    const inner = document.createElement("div");
    inner.className = "tradingview-widget-container__widget";
    inner.style.height = "100%";
    inner.style.width = "100%";
    el.appendChild(inner);

    const script = document.createElement("script");
    script.src = "https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js";
    script.type = "text/javascript";
    script.async = true;
    script.innerHTML = JSON.stringify({
      symbol: toTvSymbol(symbol),
      autosize: true,
      interval: "D",
      timezone: "Asia/Riyadh",
      theme,
      style: "1",
      locale: "ar_AE",
      allow_symbol_change: true,   // user can type any symbol
      hide_side_toolbar: false,    // drawing tools
      hide_top_toolbar: false,     // indicators / intervals
      withdateranges: true,
      details: true,
      calendar: false,
      studies: [],                 // user adds their own indicators
      support_host: "https://www.tradingview.com",
    });
    el.appendChild(script);

    return () => { el.innerHTML = ""; };
  }, [symbol, theme]);

  return (
    <div className="tradingview-widget-container" ref={containerRef} style={{ height: "100%", width: "100%" }} />
  );
}
