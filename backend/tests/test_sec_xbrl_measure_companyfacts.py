from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MEASURE_PATH = ROOT / "diagnostics" / "assessment" / "sec-xbrl-measure.py"


def _measure_module():
    spec = importlib.util.spec_from_file_location("sec_xbrl_measure", MEASURE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_sec_xbrl_measure_period_aware_includes_divided_units(monkeypatch) -> None:
    module = _measure_module()
    receipt = {
        "resolved_fact_records": [
            {
                "resolved_fact_id": "fact-eps",
                "concept": {
                    "namespace": "fasb.org/us-gaap/test",
                    "local_name": "EarningsPerShareBasic",
                    "standard": True,
                },
                "unit": {
                    "currency": "iso4217:USD",
                    "measures": ["iso4217:USD"],
                    "numerator": ["iso4217:USD"],
                    "denominator": ["xbrli:shares"],
                },
                "period": {"type": "duration", "start": "eps-start", "end": "eps-end"},
                "dimensions": {"explicit": [], "typed": []},
                "decimals": "2",
            }
        ]
    }
    sidecar = {
        "sidecar_state": module.layer3_sec_xbrl_sidecar.READY_STATE,
        "sidecar_receipt_id": "receipt-id",
        "sidecar_receipt_hash": "1" * 64,
    }
    monkeypatch.setattr(
        module.layer3_sec_xbrl_sidecar,
        "read_sec_edgar_arelle_resolved_fact_authority_sidecar_receipt",
        lambda *_args, **_kwargs: receipt,
    )
    monkeypatch.setattr(
        module.layer3_sec_xbrl_sidecar,
        "read_sec_edgar_arelle_resolved_fact_authority_internal_value_store",
        lambda _receipt: {"value_records": [{"resolved_fact_id": "fact-eps", "effective_value": "2.50"}]},
    )
    companyfacts = {
        "_value_keys": [("EarningsPerShareBasic", "USD/shares", "2.50")],
        "_value_keys_period_aware": [
            ("EarningsPerShareBasic", "USD/shares", ("d", "eps-start", "eps-end"), "2.50")
        ],
    }

    period_blind = module._companyfacts_value_match(sidecar=sidecar, companyfacts=companyfacts)
    period_aware = module._companyfacts_value_match_period_aware(sidecar=sidecar, companyfacts=companyfacts)

    assert period_blind == {"match_count": 0, "compared_count": 0, "match_rate": None}
    assert period_aware == {"match_count": 1, "compared_count": 1, "match_rate": 1.0}
