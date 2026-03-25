"""Deterministic meta-analysis layer built on top of scoring and sensitivity."""


def _factor_from_scenario_id(scenario_id: str) -> str:
    if scenario_id.startswith("cost_"):
        return "profitability"
    if scenario_id.startswith("demand_"):
        return "demand"
    if scenario_id.startswith("competition_"):
        return "competition"
    return "reviews"


def _sensitivity_level(avg_abs_delta: float) -> str:
    if avg_abs_delta >= 4.0:
        return "HIGH"
    if avg_abs_delta >= 2.0:
        return "MEDIUM"
    return "LOW"


def _build_factor_sensitivity(scenarios: list[dict]) -> list[dict]:
    bucket = {
        "profitability": [],
        "demand": [],
        "competition": [],
        "reviews": [],
    }
    for scenario in scenarios:
        factor = _factor_from_scenario_id(scenario["scenario_id"])
        bucket[factor].append(abs(scenario["score_delta"]))

    items: list[dict] = []
    for factor in ["profitability", "demand", "competition", "reviews"]:
        deltas = bucket[factor]
        avg_abs_delta = round((sum(deltas) / len(deltas)) if deltas else 0.0, 2)
        sensitivity = "UNTESTED" if not deltas else _sensitivity_level(avg_abs_delta)
        items.append(
            {
                "factor": factor,
                "avg_abs_score_delta": avg_abs_delta,
                "sensitivity_level": sensitivity,
            }
        )
    return items


def _gap_feasibility(gap_to_next_tier: float | None) -> str | None:
    if gap_to_next_tier is None:
        return None
    if gap_to_next_tier <= 5:
        return "NEAR"
    if gap_to_next_tier <= 12:
        return "MODERATE"
    return "DIFFICULT"


def _build_decision_gap(overall_score: float, decision: str) -> dict:
    if decision == "AVOID":
        gap = round(max(0.0, 55 - overall_score), 2)
        return {
            "current_score": round(overall_score, 2),
            "next_decision_tier": "WATCH",
            "gap_to_next_tier": gap,
            "feasibility": _gap_feasibility(gap),
        }
    if decision == "WATCH":
        gap = round(max(0.0, 75 - overall_score), 2)
        return {
            "current_score": round(overall_score, 2),
            "next_decision_tier": "BUY",
            "gap_to_next_tier": gap,
            "feasibility": _gap_feasibility(gap),
        }
    return {
        "current_score": round(overall_score, 2),
        "next_decision_tier": "NONE",
        "gap_to_next_tier": None,
        "feasibility": None,
    }


def _factor_label(factor: str) -> str:
    labels = {
        "profitability": "profitability",
        "demand": "demand",
        "competition": "competitive pressure",
        "reviews": "review strength",
    }
    return labels.get(factor, factor)


def _build_path_to_upgrade(
    decision: str,
    decision_gap: dict,
    features: dict,
    factor_sensitivity: list[dict],
) -> str:
    if decision == "BUY":
        return "The opportunity is already in BUY territory; focus on protecting current strengths."

    sensitivity_map = {
        item["factor"]: item["avg_abs_score_delta"] for item in factor_sensitivity
    }
    factor_scores = {
        "profitability": features["profitability_score"],
        "demand": features["demand_score"],
        "competition": features["competition_score"],
        "reviews": features["review_score"],
    }
    leverage: list[tuple[str, float]] = []
    for factor, score in factor_scores.items():
        headroom = max(0.0, 100 - score)
        leverage.append((factor, sensitivity_map.get(factor, 0.0) * headroom))
    leverage.sort(key=lambda item: item[1], reverse=True)
    primary = _factor_label(leverage[0][0])
    secondary = _factor_label(leverage[1][0])
    gap = decision_gap["gap_to_next_tier"]

    if decision == "WATCH":
        return (
            f"To move from WATCH to BUY, close about {gap:.2f} points "
            f"by prioritizing {primary}, with {secondary} as the next highest-leverage lever."
        )
    return (
        f"To move from AVOID to WATCH, close about {gap:.2f} points "
        f"by first improving {primary}, then {secondary}."
    )


def _build_recommendations(
    features: dict,
    sensitivity: dict,
    factor_sensitivity: list[dict],
    decision_result: dict,
    decision_gap: dict,
) -> list[str]:
    recs: list[str] = []

    weakest_factor = min(
        [
            ("profitability", features["profitability_score"]),
            ("demand", features["demand_score"]),
            ("competition", features["competition_score"]),
            ("reviews", features["review_score"]),
        ],
        key=lambda item: item[1],
    )[0]
    recs.append(
        f"Weakest structural signal is {_factor_label(weakest_factor)}; improve this first to raise baseline quality."
    )

    tested_factors = [
        item for item in factor_sensitivity if item["sensitivity_level"] != "UNTESTED"
    ]
    most_sensitive_factor = (
        max(tested_factors, key=lambda item: item["avg_abs_score_delta"])["factor"]
        if tested_factors
        else None
    )
    if most_sensitive_factor and most_sensitive_factor != weakest_factor:
        recs.append(
            f"Highest tested swing comes from {_factor_label(most_sensitive_factor)}; prioritize controls to reduce volatility on this lever."
        )

    if decision_result["decision"] != "BUY":
        changing_scenarios = [
            scenario for scenario in sensitivity["scenarios"] if scenario["decision_changed"]
        ]
        gap = decision_gap["gap_to_next_tier"]
        feasibility = decision_gap["feasibility"].lower()
        if changing_scenarios:
            strongest_change = max(
                changing_scenarios, key=lambda item: abs(item["score_delta"])
            )
            recs.append(
                f"Upgrade gap is {gap:.2f} points ({feasibility}); the scenario '{strongest_change['description'].lower()}' already flips the decision, making it the most practical action anchor."
            )
        else:
            recs.append(
                f"Upgrade gap is {gap:.2f} points ({feasibility}); no single tested move reaches the next tier, so combine improvements across two factors."
            )

    deduped: list[str] = []
    for rec in recs:
        if rec not in deduped:
            deduped.append(rec)
    return deduped[:3]


def _build_counterfactuals(
    decision_result: dict,
    decision_gap: dict,
    factor_sensitivity: list[dict],
    sensitivity: dict,
) -> list[str]:
    statements: list[str] = []

    tested_factors = [
        item for item in factor_sensitivity if item["sensitivity_level"] != "UNTESTED"
    ]
    strongest_factor = (
        max(tested_factors, key=lambda item: item["avg_abs_score_delta"])["factor"]
        if tested_factors
        else None
    )
    if strongest_factor:
        statements.append(
            f"{_factor_label(strongest_factor).capitalize()} is the strongest upgrade lever based on tested scenario impact."
        )

    if decision_result["decision"] == "BUY":
        statements.append("The current decision is already BUY, so no upgrade counterfactual is required.")
        return statements[:3]

    upside_scenarios = [
        scenario for scenario in sensitivity["scenarios"] if scenario["scenario_type"] == "upside"
    ]
    upgrading_upside = [scenario for scenario in upside_scenarios if scenario["decision_changed"]]

    if upgrading_upside:
        best_upgrade = max(upgrading_upside, key=lambda item: item["score_delta"])
        statements.append(
            f"A single tested upside scenario can upgrade the decision: '{best_upgrade['description'].lower()}' shifts to {best_upgrade['decision']}."
        )
    else:
        statements.append(
            f"No single tested scenario is sufficient to upgrade this opportunity to {decision_gap['next_decision_tier']}."
        )
        statements.append(
            "A stronger improvement in the most sensitive tested factor, or a combined uplift across multiple factors, would likely be required."
        )

    return statements[:3]


def _build_uncertainty_flags(features: dict, sensitivity: dict, baseline_risk: str) -> list[str]:
    flags: list[str] = []
    if features["review_score"] < 55:
        flags.append("Limited or low-quality reviews increase confidence uncertainty.")
    if features["demand_score"] < 50:
        flags.append("Demand signal is weak and could be unstable outside current assumptions.")
    if features["competition_score"] < 45:
        flags.append("High competitive intensity may compress achievable performance.")

    factor_values = [
        features["profitability_score"],
        features["demand_score"],
        features["competition_score"],
        features["review_score"],
    ]
    spread = max(factor_values) - min(factor_values)
    if spread >= 30:
        flags.append("Signals are mixed across factors, so confidence should be treated with caution.")

    if any(scenario["decision_changed"] for scenario in sensitivity["scenarios"]):
        flags.append("At least one realistic scenario changes the decision, indicating fragility.")

    downside_deltas = [
        scenario["score_delta"]
        for scenario in sensitivity["scenarios"]
        if scenario["scenario_type"] == "downside"
    ]
    if baseline_risk == "LOW" and downside_deltas and min(downside_deltas) <= -5:
        flags.append(
            "Baseline risk is low, but downside stress scenarios show meaningful deterioration."
        )

    return flags


def build_intelligence_layer(features: dict, decision_result: dict, sensitivity: dict) -> dict:
    factor_sensitivity = _build_factor_sensitivity(sensitivity["scenarios"])
    decision_gap = _build_decision_gap(
        overall_score=decision_result["overall_score"],
        decision=decision_result["decision"],
    )
    path_to_upgrade = _build_path_to_upgrade(
        decision=decision_result["decision"],
        decision_gap=decision_gap,
        features=features,
        factor_sensitivity=factor_sensitivity,
    )
    recommendations = _build_recommendations(
        features=features,
        sensitivity=sensitivity,
        factor_sensitivity=factor_sensitivity,
        decision_result=decision_result,
        decision_gap=decision_gap,
    )
    counterfactuals = _build_counterfactuals(
        decision_result=decision_result,
        decision_gap=decision_gap,
        factor_sensitivity=factor_sensitivity,
        sensitivity=sensitivity,
    )
    uncertainty_flags = _build_uncertainty_flags(
        features=features,
        sensitivity=sensitivity,
        baseline_risk=decision_result["risk_level"],
    )

    return {
        "factor_sensitivity": factor_sensitivity,
        "decision_gap": decision_gap,
        "path_to_upgrade": path_to_upgrade,
        "counterfactuals": counterfactuals,
        "recommendations": recommendations,
        "uncertainty_flags": uncertainty_flags,
    }
