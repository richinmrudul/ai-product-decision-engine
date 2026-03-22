"""Deterministic sensitivity: stress assumptions and re-run feature + decision pipeline."""

from app.schemas.analysis import ProductAnalysisRequest
from app.services.decision_engine import build_decision_result
from app.services.feature_engineering import compute_features

DECISION_RANK = {"AVOID": 0, "WATCH": 1, "BUY": 2}


def _scenario_variants(base: ProductAnalysisRequest) -> list[tuple[str, str, ProductAnalysisRequest]]:
    """Return (id, description, modified_payload) for each stress scenario."""
    cost_increased = round(base.estimated_cost * 1.15, 2)
    demand_decreased = max(0, int(round(base.estimated_monthly_sales * 0.8)))
    competitors_increased = base.competitor_count + 5

    return [
        (
            "cost_increase_15pct",
            "Estimated cost +15%",
            base.model_copy(update={"estimated_cost": cost_increased}),
        ),
        (
            "demand_decrease_20pct",
            "Estimated monthly sales -20%",
            base.model_copy(update={"estimated_monthly_sales": demand_decreased}),
        ),
        (
            "competition_increase_5",
            "Competitor count +5",
            base.model_copy(update={"competitor_count": competitors_increased}),
        ),
    ]


def _stability_from_decisions(decisions: list[str]) -> str:
    unique = len(set(decisions))
    if unique == 1:
        return "HIGH"
    if unique == 2:
        return "MEDIUM"
    return "LOW"


def _worst_case(decisions: list[str]) -> str:
    return min(decisions, key=lambda d: DECISION_RANK.get(d, 0))


def _best_case(decisions: list[str]) -> str:
    return max(decisions, key=lambda d: DECISION_RANK.get(d, 0))


def run_sensitivity_analysis(base_payload: ProductAnalysisRequest) -> dict:
    """
    Baseline decision plus three stress scenarios.
    Returns dict compatible with SensitivityAnalysis schema.
    """
    base_result = build_decision_result(compute_features(base_payload))
    all_decisions = [base_result["decision"]]

    scenarios_out: list[dict] = []
    for scenario_id, description, modified in _scenario_variants(base_payload):
        result = build_decision_result(compute_features(modified))
        all_decisions.append(result["decision"])
        scenarios_out.append(
            {
                "scenario_id": scenario_id,
                "description": description,
                "decision": result["decision"],
                "overall_score": result["overall_score"],
                "risk_level": result["risk_level"],
            }
        )

    return {
        "scenarios": scenarios_out,
        "decision_stability": _stability_from_decisions(all_decisions),
        "worst_case_decision": _worst_case(all_decisions),
        "best_case_decision": _best_case(all_decisions),
    }
