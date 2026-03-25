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
        items.append(
            {
                "factor": factor,
                "avg_abs_score_delta": avg_abs_delta,
                "sensitivity_level": _sensitivity_level(avg_abs_delta),
            }
        )
    return items


def _build_decision_gap(overall_score: float, decision: str) -> dict:
    if decision == "AVOID":
        return {
            "current_score": round(overall_score, 2),
            "next_decision_tier": "WATCH",
            "gap_to_next_tier": round(max(0.0, 55 - overall_score), 2),
        }
    if decision == "WATCH":
        return {
            "current_score": round(overall_score, 2),
            "next_decision_tier": "BUY",
            "gap_to_next_tier": round(max(0.0, 75 - overall_score), 2),
        }
    return {
        "current_score": round(overall_score, 2),
        "next_decision_tier": "BUY",
        "gap_to_next_tier": 0.0,
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
    leverage = []
    for factor, score in factor_scores.items():
        headroom = max(0.0, 100 - score)
        leverage_score = sensitivity_map.get(factor, 0.0) * headroom
        leverage.append((factor, leverage_score))
    leverage.sort(key=lambda item: item[1], reverse=True)
    primary = _factor_label(leverage[0][0])
    secondary = _factor_label(leverage[1][0])

    if decision == "WATCH":
        return (
            f"To move from WATCH to BUY, close about {decision_gap['gap_to_next_tier']:.2f} points "
            f"by prioritizing {primary}, with {secondary} as the next highest-leverage lever."
        )
    return (
        f"To move from AVOID to WATCH, close about {decision_gap['gap_to_next_tier']:.2f} points "
        f"by first improving {primary}, then {secondary}."
    )


def _build_recommendations(
    features: dict,
    sensitivity: dict,
    factor_sensitivity: list[dict],
    decision_result: dict,
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
        f"Weakest baseline signal is {_factor_label(weakest_factor)}; target this first to improve the core score."
    )

    most_sensitive_factor = max(
        factor_sensitivity, key=lambda item: item["avg_abs_score_delta"]
    )["factor"]
    recs.append(
        f"Most sensitivity sits in {_factor_label(most_sensitive_factor)}; prioritize actions that stabilize this factor to reduce swing risk."
    )

    changing_scenarios = [
        scenario for scenario in sensitivity["scenarios"] if scenario["decision_changed"]
    ]
    if changing_scenarios:
        strongest_change = max(
            changing_scenarios, key=lambda item: abs(item["score_delta"])
        )
        recs.append(
            f"Decision changes under '{strongest_change['description'].lower()}'; build a mitigation plan for this exact case."
        )
    elif decision_result["decision"] != "BUY":
        recs.append(
            f"No tested scenario changes the decision; focus on lifting demand or profitability to move toward {sensitivity['best_case_decision']}."
        )

    return recs[:4]


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
        "recommendations": recommendations,
        "uncertainty_flags": uncertainty_flags,
    }
