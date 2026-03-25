"""Deterministic sensitivity: stress assumptions and re-run feature + decision pipeline."""

from app.schemas.analysis import ProductAnalysisRequest
from app.services.decision_engine import build_decision_result
from app.services.feature_engineering import compute_features

DECISION_RANK = {"AVOID": 0, "WATCH": 1, "BUY": 2}


def _scenario_variants(
    base: ProductAnalysisRequest,
) -> list[tuple[str, str, str, ProductAnalysisRequest]]:
    """Return (id, description, impact_direction, modified_payload) for each scenario."""
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


def _decision_stability(unique_decisions: int) -> str:
    if unique_decisions <= 1:
        return "ROBUST"
    if unique_decisions == 2:
        return "MIXED"
    return "FRAGILE"


def _worst_case(decisions: list[str]) -> str:
    return min(decisions, key=lambda d: DECISION_RANK.get(d, 0))


def _best_case(decisions: list[str]) -> str:
    return max(decisions, key=lambda d: DECISION_RANK.get(d, 0))


def run_sensitivity_analysis(base_payload: ProductAnalysisRequest) -> dict:
    """
    Baseline decision plus six deterministic stress scenarios (3 downside, 3 upside).
    Reuses feature + decision pipeline; returns dict compatible with SensitivityAnalysis schema.
    """
    base_result = build_decision_result(compute_features(base_payload))
    base_decision = base_result["decision"]
    base_score = base_result["overall_score"]
    all_decisions = [base_result["decision"]]

    scenarios_out: list[dict] = []
    most_sensitive_scenario = ""
    max_abs_delta = -1.0
    largest_score_drop = 0.0
    largest_score_gain = 0.0

    for scenario_id, description, impact_direction, modified in _scenario_variants(base_payload):
        result = build_decision_result(compute_features(modified))
        scenario_score = result["overall_score"]
        score_delta = round(scenario_score - base_score, 2)
        decision_changed = result["decision"] != base_decision

        all_decisions.append(result["decision"])
        largest_score_drop = min(largest_score_drop, score_delta)
        largest_score_gain = max(largest_score_gain, score_delta)

        abs_delta = abs(score_delta)
        if abs_delta > max_abs_delta:
            max_abs_delta = abs_delta
            most_sensitive_scenario = scenario_id

        scenarios_out.append(
            {
                "scenario_id": scenario_id,
                "description": description,
                "decision": result["decision"],
                "overall_score": scenario_score,
                "score_delta": score_delta,
                "decision_changed": decision_changed,
                "risk_level": result["risk_level"],
                "impact_direction": impact_direction,
            }
        )

    unique_decisions = len(set(all_decisions))
    stability = _decision_stability(unique_decisions)
    if stability == "ROBUST":
        robustness_sentence = (
            f"Recommendation is ROBUST: baseline decision '{base_decision}' holds across all tested scenarios."
        )
    elif stability == "MIXED":
        robustness_sentence = (
            f"Recommendation is MIXED: baseline decision '{base_decision}' changes under some scenarios."
        )
    else:
        robustness_sentence = (
            f"Recommendation is FRAGILE: tested scenarios span three or more distinct decisions from baseline '{base_decision}'."
        )

    return {
        "scenarios": scenarios_out,
        "decision_stability": stability,
        "worst_case_decision": _worst_case(all_decisions),
        "best_case_decision": _best_case(all_decisions),
        "most_sensitive_scenario": most_sensitive_scenario,
        "largest_score_drop": round(largest_score_drop, 2),
        "largest_score_gain": round(largest_score_gain, 2),
        "robustness_summary": robustness_sentence,
    }
