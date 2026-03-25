"""Deterministic sensitivity: stress assumptions and re-run feature + decision pipeline."""

from app.schemas.analysis import ProductAnalysisRequest
from app.services.decision_engine import build_decision_result
from app.services.feature_engineering import compute_features

DECISION_RANK = {"AVOID": 0, "WATCH": 1, "BUY": 2}


def _scenario_variants(
    base: ProductAnalysisRequest,
) -> list[tuple[str, str, str, ProductAnalysisRequest]]:
    """Return (id, description, scenario_type, modified_payload) for each scenario."""
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


def _build_robustness_summary(
    stability: str,
    base_decision: str,
    most_sensitive_scenario_description: str,
    most_sensitive_score_delta: float,
    most_sensitive_decision_changed: bool,
    most_sensitive_decision: str,
    largest_score_drop: float,
    largest_score_gain: float,
    changed_count: int,
) -> str:
    impact_phrase = (
        f"changes the score by {most_sensitive_score_delta:+.2f} points"
    )
    if most_sensitive_decision_changed:
        decision_clause = (
            f"and shifts the decision from {base_decision} to {most_sensitive_decision}"
        )
    else:
        decision_clause = f"while keeping the decision at {base_decision}"

    if stability == "ROBUST":
        return (
            f"The recommendation appears robust around the baseline decision {base_decision}. "
            f"The most sensitive scenario is {most_sensitive_scenario_description.lower()}, which {impact_phrase} {decision_clause}. "
            f"Overall movement remains limited (max drop {largest_score_drop:.2f}, max gain {largest_score_gain:.2f})."
        )

    if stability == "MIXED":
        return (
            f"The recommendation is mixed relative to the baseline decision {base_decision}. "
            f"The key swing scenario is {most_sensitive_scenario_description.lower()}: it {impact_phrase} {decision_clause}. "
            f"Across all tested scenarios, {changed_count} scenario(s) change the baseline recommendation."
        )

    return (
        f"The recommendation is fragile around the baseline decision {base_decision}. "
        f"The most sensitive scenario is {most_sensitive_scenario_description.lower()}, which {impact_phrase} {decision_clause}. "
        f"Multiple scenarios alter the recommendation ({changed_count} changes), with score movement from {largest_score_drop:.2f} to +{largest_score_gain:.2f}."
    )


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
    most_sensitive_scenario_description = ""
    most_sensitive_score_delta = 0.0
    most_sensitive_decision_changed = False
    most_sensitive_decision = base_decision
    max_abs_delta = -1.0
    largest_score_drop = 0.0
    largest_score_gain = 0.0

    for scenario_id, description, scenario_type, modified in _scenario_variants(base_payload):
        result = build_decision_result(compute_features(modified))
        scenario_score = result["overall_score"]
        score_delta = round(scenario_score - base_score, 2)
        decision_changed = result["decision"] != base_decision
        impact_direction = "neutral"
        if score_delta > 0:
            impact_direction = "positive"
        elif score_delta < 0:
            impact_direction = "negative"

        all_decisions.append(result["decision"])
        largest_score_drop = min(largest_score_drop, score_delta)
        largest_score_gain = max(largest_score_gain, score_delta)

        abs_delta = abs(score_delta)
        if abs_delta > max_abs_delta:
            max_abs_delta = abs_delta
            most_sensitive_scenario_description = description
            most_sensitive_score_delta = score_delta
            most_sensitive_decision_changed = decision_changed
            most_sensitive_decision = result["decision"]

        scenarios_out.append(
            {
                "scenario_id": scenario_id,
                "description": description,
                "scenario_type": scenario_type,
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
    changed_count = sum(1 for scenario in scenarios_out if scenario["decision_changed"])
    robustness_sentence = _build_robustness_summary(
        stability=stability,
        base_decision=base_decision,
        most_sensitive_scenario_description=most_sensitive_scenario_description,
        most_sensitive_score_delta=most_sensitive_score_delta,
        most_sensitive_decision_changed=most_sensitive_decision_changed,
        most_sensitive_decision=most_sensitive_decision,
        largest_score_drop=round(largest_score_drop, 2),
        largest_score_gain=round(largest_score_gain, 2),
        changed_count=changed_count,
    )

    return {
        "scenarios": scenarios_out,
        "decision_stability": stability,
        "worst_case_decision": _worst_case(all_decisions),
        "best_case_decision": _best_case(all_decisions),
        "most_sensitive_scenario": most_sensitive_scenario_description,
        "largest_score_drop": round(largest_score_drop, 2),
        "largest_score_gain": round(largest_score_gain, 2),
        "robustness_summary": robustness_sentence,
    }
