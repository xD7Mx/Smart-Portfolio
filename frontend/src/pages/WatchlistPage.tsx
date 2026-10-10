import React, { useState } from "react";
import WatchlistTab from "../components/market/WatchlistTab";
import StockSheet from "../components/market/StockSheet";

/* ══ المراقبة — قسمٌ في القائمة ══ (بأمر المالك · D677)
   كانت تبويباً في المحفظة ومختبرُ الأبحاث قسماً؛ فتبادلا: المختبرُ تبويبٌ في المحفظة (شاشتُه الأولى شركاتُها)،
   والمراقبةُ قسمٌ مستقلٌّ بمكانه — بطاقةٌ لكلّ شركة، والضغطُ يفتح ورقةَ السهم نفسَها التي في كلّ مكان. */
export default function WatchlistPage() {
  const [sheet, setSheet] = useState<string | null>(null);
  return (
    <div className="fade-in">
      <WatchlistTab onOpen={setSheet} />
      {sheet && <StockSheet symbol={sheet} onClose={() => setSheet(null)} />}
    </div>
  );
}
