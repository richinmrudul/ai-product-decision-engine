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


def _build_robustness_summary(
    stability: str,
    base_decision: str,
    most_sensitive_scenario: str,
    largest_score_drop: float,
    largest_score_gain: float,
    scenarios_out: list[dict],
) -> str:
    scenario_lookup = {scenario["scenario_id"]: scenario for scenario in scenarios_out}
    sensitive = scenario_lookup.get(most_sensitive_scenario)
    sensitive_desc = sensitive["description"] if sensitive else most_sensitive_scenario
    sensitive_delta = sensitive["score_delta"] if sensitive else 0.0
    sensitive_changed = sensitive["decision_changed"] if sensitive else False
    changed_count = sum(1 for scenario in scenarios_out if scenario["decision_changed"])

    if stability == "ROBUST":
        return (
            "The recommendation appears robust across tested scenarios. "
            f"The most sensitive assumption is {sensitive_desc.lower()} ({sensitive_delta:+.2f} points), "
            f"with a maximum drop of {largest_score_drop:.2f} and a maximum gain of {largest_score_gain:.2f}."
        )

    if stability == "MIXED":
        if sensitive_changed:
            change_clause = "and changes the decision"
        else:
            change_clause = "without changing the decision"
        return (
            "The recommendation is mixed across tested scenarios. "
            f"The most sensitive assumption is {sensitive_desc.lower()} ({sensitive_delta:+.2f} points) {change_clause}. "
            f"Across all tests, {changed_count} scenario(s) move away from baseline '{base_decision}'."
        )

    return (
        "The recommendation is fragile under tested scenarios. "
        f"The most sensitive assumption is {sensitive_desc.lower()} ({sensitive_delta:+.2f} points), "
        f"and {changed_count} scenario(s) change the baseline decision '{base_decision}'. "
        f"Observed score range spans {largest_score_drop:.2f} to +{largest_score_gain:.2f} points."
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
    robustness_sentence = _build_robustness_summary(
        stability=stability,
        base_decision=base_decision,
        most_sensitive_scenario=most_sensitive_scenario,
        largest_score_drop=round(largest_score_drop, 2),
        largest_score_gain=round(largest_score_gain, 2),
        scenarios_out=scenarios_out,
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
