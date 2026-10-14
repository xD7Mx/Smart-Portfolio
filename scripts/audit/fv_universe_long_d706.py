"""كاشف D706 (قراءةٌ فقط · بأمر المالك 2026-10-14: «بياناتُ التاريخ جوهرُ توقّعات المستقبل»).

كاشفُ D701 نفسُه منذ 2019 لا 2023: لكلّ شركةٍ في كلّ ربعٍ كلُّ ما يُعرف يومها وما حدث بعد 90 و180 و365 يوماً (‏@@UNI@@) — ليُختار
للمحرّك ما يثبت في كلّ نظامٍ من السوق (ما قبل كورونا · صدمتُها · الصعود · الهبوط · ما بعده) لا في ثلاث سنواتٍ وحدها.

    docker exec sp_backend python /app/scripts/audit/fv_universe_long_d706.py
"""
import os
import runpy

os.environ["SP_BT_UNIVERSE"] = "1"
os.environ["SP_BT_FIRST"] = "2019-03"
runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "fv_backtest_d699.py"), run_name="__main__")
