"""Deterministic sensitivity: stress assumptions and re-run feature + decision pipeline."""

from app.schemas.analysis import ProductAnalysisRequest
from app.services.decision_engine import build_decision_result
from app.services.feature_engineering import compute_features

DECISION_RANK = {"AVOID": 0, "WATCH": 1, "BUY": 2}


def _scenario_variants(
    base: ProductAnalysisRequest,
) -> list[tuple[str, str, str, ProductAnalysisRequest]]:
    """Return (id, description, direction, modified_payload) for each scenario."""
    cost_increased = round(base.estimated_cost * 1.15, 2)
    cost_decreased = round(base.estimated_cost * 0.90, 2)
    demand_decreased = max(0, int(round(base.estimated_monthly_sales * 0.8)))
    demand_increased = max(0, int(round(base.estimated_monthly_sales * 1.15)))
    competitors_increased = base.competitor_count + 5
    competitors_decreased = max(0, base.competitor_count - 3)

    return [
        (
            "cost_increase_15pct",
            "Estimated cost +15%",
            "downside",
            base.model_copy(update={"estimated_cost": cost_increased}),
        ),
        (
            "demand_decrease_20pct",
            "Estimated monthly sales -20%",
            "downside",
            base.model_copy(update={"estimated_monthly_sales": demand_decreased}),
        ),
        (
            "competition_increase_5",
            "Competitor count +5",
            "downside",
            base.model_copy(update={"competitor_count": competitors_increased}),
        ),
        (
            "cost_decrease_10pct",
            "Estimated cost -10%",
            "upside",
            base.model_copy(update={"estimated_cost": cost_decreased}),
        ),
        (
            "demand_increase_15pct",
            "Estimated monthly sales +15%",
            "upside",
            base.model_copy(update={"estimated_monthly_sales": demand_increased}),
        ),
        (
            "competition_decrease_3",
            "Competitor count -3",
            "upside",
            base.model_copy(update={"competitor_count": competitors_decreased}),
        ),
    ]


def _stability_from_decision_changes(changed_count: int) -> str:
    if changed_count == 0:
        return "HIGH"
    if changed_count <= 2:
        return "MEDIUM"
    return "LOW"


def _worst_case(decisions: list[str]) -> str:
    return min(decisions, key=lambda d: DECISION_RANK.get(d, 0))


def _best_case(decisions: list[str]) -> str:
    return max(decisions, key=lambda d: DECISION_RANK.get(d, 0))


def _robustness_level(changed_count: int) -> str:
    if changed_count == 0:
        return "HIGH"
    if changed_count <= 2:
        return "MEDIUM"
    return "LOW"


def run_sensitivity_analysis(base_payload: ProductAnalysisRequest) -> dict:
    """
    Baseline decision plus three stress scenarios.
    Returns dict compatible with SensitivityAnalysis schema.
    """
    base_result = build_decision_result(compute_features(base_payload))
    base_decision = base_result["decision"]
    base_score = base_result["overall_score"]
    all_decisions = [base_result["decision"]]

    scenarios_out: list[dict] = []
    decision_changes = 0
    most_sensitive_factor = ""
    max_abs_delta = -1.0
    largest_downside_delta = 0.0
    largest_upside_delta = 0.0
    downside_retained = True

    for scenario_id, description, direction, modified in _scenario_variants(base_payload):
        result = build_decision_result(compute_features(modified))
        scenario_score = result["overall_score"]
        score_delta = round(scenario_score - base_score, 2)
        decision_changed = result["decision"] != base_decision

        all_decisions.append(result["decision"])
        if decision_changed:
            decision_changes += 1

        abs_delta = abs(score_delta)
        if abs_delta > max_abs_delta:
            max_abs_delta = abs_delta
            most_sensitive_factor = scenario_id

        if direction == "downside":
            largest_downside_delta = min(largest_downside_delta, score_delta)
            downside_retained = downside_retained and not decision_changed
        else:
            largest_upside_delta = max(largest_upside_delta, score_delta)

        scenarios_out.append(
            {
                "scenario_id": scenario_id,
                "description": description,
                "direction": direction,
                "decision": result["decision"],
                "overall_score": scenario_score,
                "score_delta": score_delta,
                "decision_changed": decision_changed,
                "risk_level": result["risk_level"],
            }
        )

    return {
        "scenarios": scenarios_out,
        "decision_stability": _stability_from_decision_changes(decision_changes),
        "worst_case_decision": _worst_case(all_decisions),
        "best_case_decision": _best_case(all_decisions),
        "robustness_summary": {
            "robustness_level": _robustness_level(decision_changes),
            "most_sensitive_factor": most_sensitive_factor,
            "largest_downside_delta": round(largest_downside_delta, 2),
            "largest_upside_delta": round(largest_upside_delta, 2),
            "baseline_decision_retained_in_downside": downside_retained,
        },
    }
