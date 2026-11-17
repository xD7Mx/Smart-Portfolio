/* طبقةُ الرسم فوق الشموع — تُرسم على لوحة الرسم نفسِها (‏D736 · المالك 2026-11-15: «سلاسةٌ ودقّةٌ وثباتٌ كتريدنق فيو»).

   كانت مستوياتُ D7M ووسومُها وخطوطُ الرسم اليدويّ عناصرَ صفحةٍ (‏DOM · SVG) يُعاد وضعُها بعد كلّ سحبٍ وتكبير — فتتأخّر عن
   الشموع إطاراً أو إطارَين وترتجف. هنا «عنصرٌ أوّليّ» تستدعيه المكتبةُ في دورة رسمها: المستوياتُ ووسومُها، وخطوطُ الاتجاه
   والقنوات، ومساراتُ الفرشاة، ونصوصُ المناطق، ووسومُ المحور المؤطَّرة (‏D713: إطارٌ بلون الخطّ لا كتلةٌ مملوءة) — كلُّها
   تتحرّك مع الشموع في الإطار نفسِه. والإحداثيُّ الأفقيّ «منطقيّ» (رقمُ الشمعة وكسرُها) فيمتدّ الخطُّ يمينَ آخر شمعة. */
import type { ISeriesApi, ISeriesPrimitive, SeriesAttachedParameter, SeriesType, Time, IChartApi, Logical } from "lightweight-charts";
import type { CanvasRenderingTarget2D } from "fancy-canvas";
import { fmtPrice } from "./chartData";

export type Level = {
  price: number; color: string; text?: string; width?: number; dash?: number[];
  rank?: number;            // الأصغرُ أَولى بالوسم حين تتزاحم
  tag?: boolean;            // وسمٌ مؤطَّر على محور الأسعار
  bold?: boolean; line?: boolean;
  /* ‏D756 (المالك 2026-11-16): «أرقامُ المستويات أمام آخر شمعة كتريدنق فيو — لا في عمود الأسعار — فوق الخطّ أو عليه أو تحته، وبحوافّ واضحة» */
  label?: string; lx?: number; lpos?: "above" | "on" | "below"; lcolor?: string;
};
export type Segment = { x1: number; y1: number; x2: number; y2: number; color: string; width?: number; dash?: number[]; extend?: boolean };
export type Path = { pts: { x: number; y: number }[]; color: string; width?: number };
export type Note = { x: number; y: number; text: string; color: string };
export type Band = { p1: number; p2: number; color: string };       // تظليلٌ بين سعرين على عرض اللوحة (مناطقُ D7M · D744)

/** خلفيةٌ بين مستويين في لوحة مؤشّر — ‏fill(h0, h1) في سكربت تريدنق فيو (‏Stoch RSI بين 80 و20 · D741). */
export class BandFill implements ISeriesPrimitive<Time> {
  private s: ISeriesApi<SeriesType> | null = null;
  constructor(private hi: number, private lo: number, private color: string) {}
  attached(p: SeriesAttachedParameter<Time>) { this.s = p.series; }
  detached() { this.s = null; }
  paneViews() {
    return [{ zOrder: () => "bottom" as const, renderer: () => ({ draw: (t: CanvasRenderingTarget2D) => t.useMediaCoordinateSpace(({ context: c, mediaSize }) => {
      const a = this.s?.priceToCoordinate(this.hi), b = this.s?.priceToCoordinate(this.lo);
      if (a == null || b == null) return;
      c.fillStyle = this.color;
      c.fillRect(0, Math.min(a as number, b as number), mediaSize.width, Math.abs((b as number) - (a as number)));
    }) }) }];
  }
}

export class ChartOverlay implements ISeriesPrimitive<Time> {
  private chart: IChartApi | null = null;
  private series: ISeriesApi<SeriesType> | null = null;
  private req: (() => void) | null = null;
  levels: Level[] = [];
  segments: Segment[] = [];
  paths: Path[] = [];
  notes: Note[] = [];
  bands: Band[] = [];
  font = "sans-serif";
  bg = "#ffffff";
  textTop = 12;             // أسماءُ المستويات لا تُكتب فوق هذا الحدّ — مكانُ وسيلة الإيضاح

  attached(p: SeriesAttachedParameter<Time>) { this.chart = p.chart as IChartApi; this.series = p.series; this.req = p.requestUpdate; }
  detached() { this.chart = this.series = this.req = null; }
  set(part: Partial<Pick<ChartOverlay, "levels" | "segments" | "paths" | "notes" | "bands" | "font" | "bg" | "textTop">>) {
    Object.assign(this, part);
    this.req?.();
  }

  /* المكتبةُ لا تقبل رقمَ شمعةٍ كسرياً (تعيد صفراً فيُرسم الخطُّ على حافّة الرسم) — فيُحسب موضعُ الشمعة الصحيحة ويُضاف كسرُها بعرض الشمعة */
  private px(x: number): number | null {
    const ts = this.chart?.timeScale();
    if (!ts || !isFinite(x)) return null;
    const k = Math.floor(x), c = ts.logicalToCoordinate(k as Logical);
    return c == null ? null : (c as number) + (x - k) * ts.options().barSpacing;
  }
  private py(p: number): number | null {
    const c = this.series?.priceToCoordinate(p);
    return c == null ? null : (c as number);
  }

  paneViews() {
    return [{ zOrder: () => "normal" as const, renderer: () => ({ draw: (t: CanvasRenderingTarget2D) => this.drawPane(t) }) }];
  }
  priceAxisPaneViews() {
    return [{ zOrder: () => "normal" as const, renderer: () => ({ draw: (t: CanvasRenderingTarget2D) => this.drawAxis(t) }) }];
  }

  private drawPane(target: CanvasRenderingTarget2D) {
    target.useMediaCoordinateSpace(({ context: ctx, mediaSize }) => {
      const W = mediaSize.width, H = mediaSize.height;
      ctx.save();
      ctx.lineCap = "round"; ctx.lineJoin = "round";
      for (const z of this.bands) {
        const a = this.py(z.p1), b = this.py(z.p2);
        if (a == null || b == null) continue;
        ctx.fillStyle = z.color;
        ctx.fillRect(0, Math.min(a, b), W, Math.max(1, Math.abs(b - a)));
      }
      // ١ المستويات: خطٌّ على عرض اللوحة
      for (const l of this.levels) {
        if (l.line === false) continue;
        const y = this.py(l.price);
        if (y == null || y < -2 || y > H + 2) continue;
        ctx.beginPath();
        ctx.strokeStyle = l.color; ctx.lineWidth = l.width ?? 1; ctx.setLineDash(l.dash ?? []);
        const yy = Math.round(y) + 0.5;
        ctx.moveTo(0, yy); ctx.lineTo(W, yy); ctx.stroke();
      }
      ctx.setLineDash([]);
      // ٢ القطع: خطوطُ الاتجاه والقنوات والرسمُ اليدويّ
      for (const s of this.segments) {
        const x1 = this.px(s.x1), x2 = this.px(s.x2), y1 = this.py(s.y1), y2 = this.py(s.y2);
        if (x1 == null || x2 == null || y1 == null || y2 == null) continue;
        let ex = x2, ey = y2;
        if (s.extend && x2 !== x1) { const k = (y2 - y1) / (x2 - x1); ex = W; ey = y2 + k * (W - x2); }
        ctx.beginPath();
        ctx.strokeStyle = s.color; ctx.lineWidth = s.width ?? 1.5; ctx.setLineDash(s.dash ?? []);
        ctx.moveTo(x1, y1); ctx.lineTo(ex, ey); ctx.stroke();
      }
      ctx.setLineDash([]);
      // ٣ مساراتُ الفرشاة
      for (const p of this.paths) {
        let started = false;
        ctx.beginPath();
        ctx.strokeStyle = p.color; ctx.lineWidth = p.width ?? 2;
        for (const q of p.pts) {
          const x = this.px(q.x), y = this.py(q.y);
          if (x == null || y == null) continue;
          if (started) ctx.lineTo(x, y); else { ctx.moveTo(x, y); started = true; }
        }
        if (started) ctx.stroke();
      }
      // ٤ النصوص: اسمُ المستوى على يسار الرسم (كتريدنق فيو)، ونصوصُ المناطق — ولا يتراكب نصّان
      ctx.textBaseline = "alphabetic";
      const placed: number[] = [];
      ctx.font = `600 10px ${this.font}`;
      ctx.textAlign = "left";
      for (const l of [...this.levels].filter(x => x.text).sort((a, b) => (a.rank ?? 9) - (b.rank ?? 9))) {
        const y = this.py(l.price);
        if (y == null || y < this.textTop || y > H - 4 || placed.some(o => Math.abs(o - y) < 12)) continue;
        placed.push(y);
        ctx.fillStyle = l.color;
        ctx.fillText(l.text as string, 8, y - 4);
      }
      // ٤ب أرقامُ المستويات أمام آخر شمعة (‏D761 · المالك: «الرقمُ سادةً بلا دائرةٍ ولا تعليم، على الخطّ نفسِه، ولونُه لونُ خطّه»):
      // نصٌّ وحدَه بلون الخطّ — وعلى الخطّ تُفرَج له فُسحةٌ بلون اللوحة كي لا يشطبه الخطّ (لا إطارَ ولا حبّة) — ولا يتراكب رقمان
      ctx.font = `700 10.5px ${this.font}`;
      ctx.textBaseline = "middle";
      const boxes: [number, number][] = [];
      for (const l of [...this.levels].filter(x => x.label).sort((a, b) => (a.rank ?? 9) - (b.rank ?? 9))) {
        const y = this.py(l.price), x = l.lx != null ? this.px(l.lx) : null;
        if (y == null || x == null || y < this.textTop || y > H - 4) continue;
        const h = 13, w = ctx.measureText(l.label as string).width + 6;
        const cy = l.lpos === "above" ? y - h / 2 - 1 : l.lpos === "below" ? y + h / 2 + 1 : y;
        let top = Math.round(cy - h / 2);
        // مستويان متقاربان: يُزاح الرقمُ الثاني عن الأوّل (لا يُحذف)، في اتّجاه موضعه
        for (let k = 0; k < 4 && boxes.some(([a, b]) => top < b + 1 && top + h > a - 1); k++) {
          const hit = boxes.find(([a, b]) => top < b + 1 && top + h > a - 1)!;
          top = l.lpos === "above" ? hit[0] - h - 1 : hit[1] + 1;
        }
        if (boxes.some(([a, b]) => top < b && top + h > a) || top < this.textTop || top + h > H) continue;
        boxes.push([top, top + h]);
        const xx = Math.round(Math.min(Math.max(x, 4), W - w - 4));
        if ((l.lpos || "on") === "on" && Math.abs(top + h / 2 - y) < h) { ctx.fillStyle = this.bg; ctx.fillRect(xx, top, w, h); }
        ctx.fillStyle = l.lcolor || l.color;
        ctx.textAlign = "left";
        ctx.fillText(l.label as string, xx + 3, top + h / 2 + 0.5);
      }
      ctx.textBaseline = "alphabetic";
      const placedN: { x: number; y: number }[] = [];
      ctx.font = `700 10.5px ${this.font}`;
      ctx.textAlign = "center";
      for (const n of this.notes) {
        const x = this.px(n.x), y = this.py(n.y);
        if (x == null || y == null || y < 10 || y > H - 4 || placedN.some(o => Math.abs(o.y - y) < 14 && Math.abs(o.x - x) < 90)) continue;
        placedN.push({ x, y });
        ctx.fillStyle = n.color;
        ctx.fillText(n.text, Math.min(Math.max(x, 40), W - 40), y + 3.5);
      }
      ctx.restore();
    });
  }

  private drawAxis(target: CanvasRenderingTarget2D) {
    target.useMediaCoordinateSpace(({ context: ctx, mediaSize }) => {
      const W = mediaSize.width, H = mediaSize.height;
      const placed: number[] = [];
      ctx.save();
      ctx.textAlign = "center"; ctx.textBaseline = "middle";
      for (const l of [...this.levels].filter(x => x.tag).sort((a, b) => (a.rank ?? 9) - (b.rank ?? 9))) {
        const y = this.py(l.price);
        if (y == null || y < 9 || y > H - 9 || placed.some(o => Math.abs(o - y) < 17)) continue;
        placed.push(y);
        const h = 17, w = Math.max(40, W - 5), x = 2, top = Math.round(y - h / 2) + 0.5;
        ctx.beginPath();
        if (typeof (ctx as any).roundRect === "function") (ctx as any).roundRect(x + 0.5, top, w, h, 4); else ctx.rect(x + 0.5, top, w, h);
        ctx.fillStyle = this.bg; ctx.fillRect(x, top - 2.5, w + 1, h + 5); ctx.fill();
        ctx.strokeStyle = l.color; ctx.lineWidth = l.bold ? 1.6 : 1; ctx.stroke();
        ctx.fillStyle = l.color;
        ctx.font = `${l.bold ? 800 : 600} 11px ${this.font}`;
        ctx.fillText(fmtPrice(l.price), x + 0.5 + w / 2, top + h / 2 + 0.5);
      }
      ctx.restore();
    });
  }
}
