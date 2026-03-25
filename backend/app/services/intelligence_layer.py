"""Deterministic meta-analysis layer built on top of scoring and sensitivity."""

DECISION_RANK = {"AVOID": 0, "WATCH": 1, "BUY": 2}


def _factor_from_scenario_id(scenario_id: str) -> str:
    if scenario_id.startswith("cost_"):
        return "profitability"
    if scenario_id.startswith("demand_"):
        return "demand"
    if scenario_id.startswith("competition_"):
        return "competition"
    if scenario_id.startswith("review_") or scenario_id.startswith("average_rating_"):
        return "reviews"
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


def _strongest_upside_and_downside(scenarios: list[dict]) -> tuple[dict | None, dict | None]:
    upside = [scenario for scenario in scenarios if scenario["scenario_type"] == "upside"]
    downside = [scenario for scenario in scenarios if scenario["scenario_type"] == "downside"]
    strongest_upside = max(upside, key=lambda item: item["score_delta"]) if upside else None
    strongest_downside = min(downside, key=lambda item: item["score_delta"]) if downside else None
    return strongest_upside, strongest_downside


def _build_path_to_upgrade(
    decision: str,
    decision_gap: dict,
    features: dict,
    factor_sensitivity: list[dict],
    sensitivity: dict,
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
    strongest_upside, _ = _strongest_upside_and_downside(sensitivity["scenarios"])
    if strongest_upside:
        upside_factor = _factor_label(_factor_from_scenario_id(strongest_upside["scenario_id"]))
        upside_upgrade = DECISION_RANK.get(strongest_upside["decision"], 0) > DECISION_RANK.get(decision, 0)
        if upside_upgrade:
            return (
                f"{upside_factor.capitalize()} is the strongest tested upgrade lever. "
                f"A single tested improvement ('{strongest_upside['description'].lower()}') moves the decision from {decision} to {strongest_upside['decision']}."
            )
        return (
            f"{upside_factor.capitalize()} is the strongest tested upgrade lever, but even the best single tested improvement "
            f"('{strongest_upside['description'].lower()}') is not enough to reach {decision_gap['next_decision_tier']}. "
            f"A combined lift across {primary} and {secondary} is likely required."
        )

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
    weakest_actions = {
        "profitability": "Improve margin cushion by reducing unit cost or tightening pricing discipline.",
        "demand": "Validate stronger demand with targeted acquisition tests before scaling spend.",
        "competition": "Reduce competitive exposure by sharpening differentiation in crowded segments.",
        "reviews": "Strengthen review credibility by improving rating quality and review volume.",
    }
    recs.append(weakest_actions[weakest_factor])

    tested_factors = [
        item for item in factor_sensitivity if item["sensitivity_level"] != "UNTESTED"
    ]
    most_sensitive_factor = (
        max(tested_factors, key=lambda item: item["avg_abs_score_delta"])["factor"]
        if tested_factors
        else None
    )
    if most_sensitive_factor and most_sensitive_factor != weakest_factor:
        sensitive_actions = {
            "profitability": "Protect profitability volatility with tighter cost controls and supplier negotiation guardrails.",
            "demand": "Stabilize demand risk with repeated demand validation before committing inventory.",
            "competition": "Mitigate competitive fragility by focusing on defensible positioning and niche channels.",
            "reviews": "Reduce review-driven swing risk by lifting post-purchase experience and response quality.",
        }
        recs.append(sensitive_actions[most_sensitive_factor])

    if decision_result["decision"] != "BUY":
        changing_scenarios = [s for s in sensitivity["scenarios"] if s["decision_changed"]]
        strongest_upside, _ = _strongest_upside_and_downside(sensitivity["scenarios"])
        gap = decision_gap["gap_to_next_tier"]
        feasibility = decision_gap["feasibility"].lower()
        if strongest_upside and DECISION_RANK.get(strongest_upside["decision"], 0) > DECISION_RANK.get(decision_result["decision"], 0):
            recs.append(
                f"Most realistic upgrade path is '{strongest_upside['description'].lower()}': it already lifts the decision to {strongest_upside['decision']}."
            )
        elif changing_scenarios:
            strongest_change = max(changing_scenarios, key=lambda item: abs(item["score_delta"]))
            recs.append(
                f"Upgrade gap is {gap:.2f} points ({feasibility}); '{strongest_change['description'].lower()}' is the closest tested lever, but additional improvement is still needed."
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
    strongest_upside, strongest_downside = _strongest_upside_and_downside(sensitivity["scenarios"])

    if strongest_factor:
        statements.append(
            f"{_factor_label(strongest_factor).capitalize()} is the strongest upgrade lever based on tested scenario impact."
        )

    if strongest_upside:
        statements.append(
            f"Strongest tested upside scenario is '{strongest_upside['description'].lower()}' ({strongest_upside['score_delta']:+.2f} points)."
        )
    if strongest_downside:
        statements.append(
            f"Strongest tested downside scenario is '{strongest_downside['description'].lower()}' ({strongest_downside['score_delta']:+.2f} points)."
        )

    if decision_result["decision"] == "BUY":
        if strongest_downside and strongest_upside:
            if abs(strongest_downside["score_delta"]) > strongest_upside["score_delta"]:
                statements.append("Downside fragility is stronger than upside potential under tested assumptions.")
        statements.append("The current decision is already BUY, so no upgrade counterfactual is required.")
        return statements[:3]

    upside_scenarios = [
        scenario for scenario in sensitivity["scenarios"] if scenario["scenario_type"] == "upside"
    ]
    current_rank = DECISION_RANK.get(decision_result["decision"], 0)
    upgrading_upside = [
        scenario
        for scenario in upside_scenarios
        if DECISION_RANK.get(scenario["decision"], 0) > current_rank
    ]

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

    if strongest_downside and strongest_upside:
        if abs(strongest_downside["score_delta"]) > strongest_upside["score_delta"]:
            statements.append("Downside fragility is stronger than upside potential in the tested range.")
        else:
            statements.append("Upside potential is at least as strong as downside fragility in the tested range.")

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
        sensitivity=sensitivity,
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
