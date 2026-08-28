"""
Finance Agent — Smart Portfolio
=================================
Analyzes the financial strength of companies.
Produces Finance Score, Sharia check, and expert ratings summary.

Responsibility: Financial quality assessment ONLY.
Cannot: modify data, make buy/sell decisions.
"""

from app.agents.base import BaseAgent


SYSTEM_PROMPT = """
أنت محلل مالي محترف متخصص في تحليل الشركات المدرجة في الأسواق المالية.
مهمتك: تحليل القوة المالية للشركة بناءً على البيانات المتوفرة.

قواعد صارمة:
1. اعتمد على البيانات المقدمة فقط — لا تفترض معلومات غير موجودة.
2. كل استنتاج يجب أن يكون مدعوماً بدليل واضح.
3. لا تصدر توصية شراء أو بيع مباشرة.
4. وضح درجة ثقتك في التحليل (0-100).
5. إذا كانت البيانات غير كاملة، أشر إلى ذلك صراحةً.

أنت تقدم دعماً للقرار، وليس قراراً بديلاً.
"""


class FinanceAgent(BaseAgent):
    name = "FinanceAgent"
    description = "Analyzes financial quality: earnings, cash flow, debt, sustainability."

    async def _analyze(self, context: dict) -> dict:
        company_data = context.get("company_data", {})
        symbol = context.get("symbol", "N/A")

        if not company_data:
            return {
                "summary": f"No financial data available for {symbol}.",
                "score": None,
                "confidence": 0,
                "evidence": [],
            }

        prompt = self._build_prompt(symbol, company_data)
        ai_response = await self._ask_ai(prompt, SYSTEM_PROMPT)

        # Parse key metrics for scoring
        score = self._calculate_score(company_data)

        return {
            "summary": ai_response[:1000],
            "score": score,
            "confidence": 75,
            "evidence": self._extract_evidence(company_data),
            "suggested_action": "Review AI analysis for decision support.",
            "data": {
                "symbol": symbol,
                "finance_score": score,
                "ai_analysis": ai_response,
            },
        }

    def _build_prompt(self, symbol: str, data: dict) -> str:
        return f"""
تحليل مالي للشركة: {symbol}

البيانات المتوفرة:
- الإيرادات: {data.get('revenue', 'غير متوفر')}
- صافي الربح: {data.get('net_income', 'غير متوفر')}
- هامش الربح: {data.get('profit_margin', 'غير متوفر')}%
- التدفق النقدي الحر: {data.get('free_cash_flow', 'غير متوفر')}
- نسبة الدين إلى الحقوق: {data.get('debt_to_equity', 'غير متوفر')}
- العائد على حقوق الملكية: {data.get('roe', 'غير متوفر')}%
- نمو الأرباح (3 سنوات): {data.get('earnings_growth_3y', 'غير متوفر')}%

المطلوب:
1. تقييم جودة الأرباح.
2. تقييم سلامة التدفق النقدي.
3. تقييم مستوى المديونية.
4. الاستدامة المالية على المدى الطويل.
5. نقاط القوة والضعف الرئيسية.
6. درجة ثقتك في التحليل (0-100).

الرد يجب أن يكون منظماً ومختصراً.
"""

    def _calculate_score(self, data: dict) -> float:
        """Rule-based pre-scoring before AI analysis."""
        score = 50.0
        try:
            if data.get("profit_margin", 0) > 15:
                score += 10
            if data.get("roe", 0) > 15:
                score += 10
            if data.get("debt_to_equity", 999) < 1:
                score += 10
            if data.get("free_cash_flow", 0) > 0:
                score += 10
            if data.get("earnings_growth_3y", 0) > 5:
                score += 10
        except Exception:
            pass
        return min(score, 100)

    def _extract_evidence(self, data: dict) -> list:
        evidence = []
        for key, label in [
            ("revenue", "Revenues"),
            ("net_income", "Net Income"),
            ("profit_margin", "Profit Margin"),
            ("roe", "Return on Equity"),
            ("debt_to_equity", "Debt-to-Equity"),
        ]:
            if data.get(key) is not None:
                evidence.append({"metric": label, "value": data[key]})
        return evidence
