"""Market parameters. Nothing is hard-coded here; everything is loaded, dated and guarded."""
from __future__ import annotations
import json, datetime as dt
from dataclasses import dataclass
from pathlib import Path

CONFIG_DIR = Path(__file__).resolve().parents[2] / "data" / "fv_config"


class ParamsError(RuntimeError):
    pass


@dataclass(frozen=True)
class Params:
    raw: dict

    # ---- guarded scalars ----
    @property
    def risk_free(self) -> float:
        node = self.raw["risk_free_sar"]
        v = node.get("value")
        if v is None:
            raise ParamsError(
                "risk_free_sar.value غير معبأ — المحرك لا يعمل بمعدل خالٍ من المخاطر مفترض. "
                "املأ القيمة وتاريخها في config/market_params.json"
            )
        lo, hi = node["sanity_range"]
        if not (lo <= v <= hi):
            raise ParamsError(f"risk_free_sar={v} خارج نطاق المعقولية {node['sanity_range']}")
        return float(v)

    @property
    def erp(self) -> float:
        return float(self.raw["erp"]["selected"])

    @property
    def tax(self) -> float:
        return float(self.raw["tax_rate"]["value"])

    @property
    def eng(self) -> dict:
        return self.raw["engine"]

    def unlevered_beta(self, tadawul_sector: str) -> tuple[float, bool]:
        """Returns (beta, is_verified). Unverified betas cost one confidence grade."""
        tbl = self.raw["unlevered_sector_betas"]
        verified = tbl.get("_status") == "verified"
        if tadawul_sector not in tbl:
            raise ParamsError(f"لا توجد بيتا قطاعية لـ «{tadawul_sector}»")
        return float(tbl[tadawul_sector]), verified

    # ---- provenance, carried into every output ----
    def provenance(self) -> dict:
        return {
            "params_as_of": self.raw["as_of"],
            "erp_source": self.raw["erp"]["source"],
            "erp_selected": self.raw["erp"]["selected"],
            "risk_free_as_of": self.raw["risk_free_sar"].get("as_of"),
            "betas_verified": self.raw["unlevered_sector_betas"].get("_status") == "verified",
            "params_verified": bool(self.raw.get("verified")),
        }


def load_params(path: Path | None = None, *, allow_unverified: bool = False,
                allow_stale: bool = False) -> Params:
    path = path or (CONFIG_DIR / "market_params.json")
    raw = json.loads(path.read_text(encoding="utf-8"))

    age = (dt.date.today() - dt.date.fromisoformat(raw["as_of"])).days
    if age > raw["max_age_days"] and not allow_stale:
        raise ParamsError(
            f"ملف المعايير عمره {age} يوماً (الحد {raw['max_age_days']}). "
            "أعد قراءة علاوة المخاطر والمعدل الخالي من المخاطر قبل التشغيل. "
            "داموداران يحدّث مخاطر الدول في يوليو — اقرأ إصدار 2026-07 قبل أي قياس اعتمادي."
        )
    if not raw.get("verified") and not allow_unverified:
        raise ParamsError(
            "verified=false في config/market_params.json. "
            "المحرك يرفض إنتاج قيم اعتمادية بمعايير غير موثّقة. "
            "شغّل بـ allow_unverified=True للتجارب فقط — ومخرجاتها تُعلَّم غير اعتمادية."
        )
    return Params(raw)
