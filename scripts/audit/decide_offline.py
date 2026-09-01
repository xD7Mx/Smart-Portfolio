"""تشغيلُ الحسم بلا سوقٍ حيّة — مسبارٌ يقوم مقام المصدر.

## لماذا

‏`decide.py` لا يعمل إلّا بمنفذٍ إلى ياهو، فكان كلُّ تعديلٍ فيه يُشحن
غيرَ مُجرَّب ويُختبر أوّلَ مرّةٍ على خادم المالك. وقد أسقط ذلك تشغيلين:
مرّةً بـKeyError على شركةٍ بلا نموذج، ومرّةً باختبارِ عدٍّ يقيس قبل
اكتمال الجدول. كلاهما كان يظهر هنا في ثوانٍ.

**الأرقامُ التي يخرجها بلا معنًى استثماريّ** — القوائمُ مولَّدةٌ عشوائياً.
المقصودُ وحده أن يُنفَّذ كلُّ مسارٍ في الشيفرة، وأن تُقرأ سطورُ السلامة
كلُّها قبل الشحن. ويُطابق تعدادَ السوق: خمسٌ بلا قوائم والباقي لها.

    python scripts/audit/decide_offline.py
"""

import sys, types, asyncio, random
sys.path.insert(0,'backend'); sys.path.insert(0,'.')
from app.data.market_universe import MARKET_UNIVERSE as U
from app.data import universe as uni
MAIN = sorted(uni.main_market(U))
# نفسُ تعداد الخادم: 5 بلا قوائم، والباقي 268 لها قوائم
NOPER = set(['1324','7205','2002','8270','4010'][:5])
random.seed(11)
mod = types.ModuleType("app.services.market_data")
def _periods(sym):
    if sym in NOPER: return {"periods": []}
    ps=[]
    for i in range(random.choice([2,5,6])):
        eq=random.uniform(1e8,9e9)
        ps.append({"year":2019+i,"net_income":random.uniform(-2e8,1.5e9),"equity":eq,
          "revenue":random.uniform(5e8,2e10),"operating_income":random.uniform(-1e8,2e9),
          "depreciation":random.uniform(1e7,3e8),"total_debt":random.uniform(0,5e9),
          "ending_cash":random.uniform(1e7,2e9),"eps":random.uniform(-1,9),
          "shares_outstanding":random.uniform(1e7,3e9),
          "operating_cash_flow":random.uniform(-1e8,3e9),
          "dividends_paid":-abs(random.uniform(0,5e8)),
          "total_assets":eq*random.uniform(1.2,6.0),
          "interest_expense":random.uniform(1e6,4e8)})
    return {"periods":ps}
class MS:
    async def get_financials(self,t,allow_supplement=False): return _periods(t.split('.')[0])
    async def get_company_info(self,t):
        return {"current_price":random.uniform(8,300),
                "dividend_per_share":random.choice([0,random.uniform(0.2,6)])}
mod.market_service=MS(); sys.modules["app.services.market_data"]=mod
import importlib.util
spec=importlib.util.spec_from_file_location("dec","scripts/audit/decide.py")
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
sys.exit(asyncio.run(m.main([])))
