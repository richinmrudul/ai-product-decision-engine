"""Deterministic calibration: explain confidence, risk posture, threshold reasoning, and synthesis."""

from app.services.decision_engine import WEIGHTS, clamp


FACTOR_SCORE_KEYS = {
    "profitability": "profitability_score",
    "demand": "demand_score",
    "competition": "competition_score",
    "reviews": "review_score",
}

CONFIDENCE_COMPONENT_WEIGHTS = {
    "signal_consistency": 0.35,
    "data_support": 0.30,
    "scenario_robustness": 0.35,
}


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


def _factor_spread(features: dict) -> float:
    scores = [
        features["profitability_score"],
        features["demand_score"],
        features["competition_score"],
        features["review_score"],
    ]
    return max(scores) - min(scores)


def _raw_confidence_components(features: dict, sensitivity: dict) -> dict:
    spread = _factor_spread(features)
    signal_consistency = round(clamp(100 - spread, 0, 100), 2)

    review_count = features.get("review_count", 0)
    demand_score = features["demand_score"]
    review_score = features["review_score"]
    data_points = 0
    if review_count >= 200:
        data_points += 40
    elif review_count >= 50:
        data_points += 25
    elif review_count >= 10:
        data_points += 12
    if demand_score >= 50:
        data_points += 30
    elif demand_score >= 35:
        data_points += 18
    if review_score >= 55:
        data_points += 30
    elif review_score >= 45:
        data_points += 18
    data_support = round(clamp(float(data_points), 0, 100), 2)

    downside_deltas = [
        s["score_delta"] for s in sensitivity["scenarios"] if s["score_delta"] < 0
    ]
    worst_down = min(downside_deltas) if downside_deltas else 0.0
    changed = sum(1 for s in sensitivity["scenarios"] if s["decision_changed"])
    stability = sensitivity["decision_stability"]
    scenario_robustness = 70.0
    if stability == "ROBUST":
        scenario_robustness += 20
    elif stability == "MIXED":
        scenario_robustness -= 5
    else:
        scenario_robustness -= 25
    scenario_robustness -= min(30, abs(worst_down) * 2)
    scenario_robustness -= changed * 8
    scenario_robustness = round(clamp(scenario_robustness, 0, 100), 2)

    return {
        "signal_consistency": signal_consistency,
        "data_support": data_support,
        "scenario_robustness": scenario_robustness,
    }


def _build_confidence_breakdown(features: dict, decision_result: dict, sensitivity: dict) -> dict:
    components = _raw_confidence_components(features, sensitivity)
    signal_consistency = components["signal_consistency"]
    data_support = components["data_support"]
    scenario_robustness = components["scenario_robustness"]

    weighted_contributions = {
        name: round(CONFIDENCE_COMPONENT_WEIGHTS[name] * components[name], 2)
        for name in CONFIDENCE_COMPONENT_WEIGHTS
    }
    aggregated = round(sum(weighted_contributions.values()), 2)
    final_confidence = round(clamp(aggregated, 35, 95), 2)

    component_values = {
        "signal_consistency": signal_consistency,
        "data_support": data_support,
        "scenario_robustness": scenario_robustness,
    }
    weakest_confidence_component = min(
        component_values, key=lambda k: component_values[k]
    )

    pipeline_confidence = decision_result["confidence_score"]
    confidence_explanation = (
        f"Confidence is the weighted sum of three 0–100 components "
        f"({CONFIDENCE_COMPONENT_WEIGHTS['signal_consistency']:.0%} signal_consistency + "
        f"{CONFIDENCE_COMPONENT_WEIGHTS['data_support']:.0%} data_support + "
        f"{CONFIDENCE_COMPONENT_WEIGHTS['scenario_robustness']:.0%} scenario_robustness), "
        f"clamped to [35, 95], yielding {final_confidence}. "
        f"The weakest component is {weakest_confidence_component.replace('_', ' ')}. "
        f"For comparison, the scoring pipeline also reports confidence {pipeline_confidence} "
        f"(overall score minus a spread-based penalty)."
    )

    return {
        "signal_consistency": signal_consistency,
        "data_support": data_support,
        "scenario_robustness": scenario_robustness,
        "component_weights": CONFIDENCE_COMPONENT_WEIGHTS,
        "weighted_contributions": weighted_contributions,
        "aggregated_component_score": aggregated,
        "weakest_confidence_component": weakest_confidence_component,
        "pipeline_confidence": pipeline_confidence,
        "final_confidence": final_confidence,
        "confidence_explanation": confidence_explanation,
    }


def _max_positive_overall_lift_per_factor(scenarios: list[dict]) -> dict[str, float]:
    per: dict[str, float] = {
        "profitability": 0.0,
        "demand": 0.0,
        "competition": 0.0,
        "reviews": 0.0,
    }
    for s in scenarios:
        if s["score_delta"] <= 0:
            continue
        f = _factor_from_scenario_id(s["scenario_id"])
        per[f] = max(per[f], s["score_delta"])
    return per


def _build_threshold_analysis(
    features: dict,
    decision_result: dict,
    sensitivity: dict,
    intelligence: dict,
) -> dict:
    decision_gap = intelligence["decision_gap"]
    gap = decision_gap.get("gap_to_next_tier")
    next_tier = decision_gap.get("next_decision_tier", "NONE")

    if gap is None or next_tier == "NONE":
        return {
            "next_tier": "NONE",
            "gap_overall_points": None,
            "strongest_single_factor_lever": "none",
            "estimated_factor_score_points_needed": None,
            "single_factor_upgrade_feasible": False,
            "threshold_summary": "No further tier upgrade applies; baseline is already at the top decision band.",
        }

    gap = float(gap)
    if gap <= 0:
        return {
            "next_tier": next_tier,
            "gap_overall_points": round(gap, 2),
            "strongest_single_factor_lever": "none",
            "estimated_factor_score_points_needed": None,
            "single_factor_upgrade_feasible": True,
            "threshold_summary": f"Baseline overall score already meets the {next_tier} threshold; no positive gap remains.",
        }
    per_factor_lift = _max_positive_overall_lift_per_factor(sensitivity["scenarios"])
    strongest_lever = max(per_factor_lift, key=lambda k: per_factor_lift[k])
    max_lift_strongest = per_factor_lift[strongest_lever]
    label = {
        "profitability": "profitability",
        "demand": "demand",
        "competition": "competition",
        "reviews": "reviews",
    }[strongest_lever]

    w = WEIGHTS[strongest_lever]
    needed_factor_points = round(gap / w, 2) if w > 0 else None
    score_key = FACTOR_SCORE_KEYS[strongest_lever]
    headroom = max(0.0, 100.0 - features[score_key])

    single_factor_upgrade_feasible = any(
        s["score_delta"] >= gap - 1e-6
        for s in sensitivity["scenarios"]
        if s["score_delta"] > 0
    )

    if single_factor_upgrade_feasible:
        best = max(
            (s for s in sensitivity["scenarios"] if s["score_delta"] > 0),
            key=lambda s: s["score_delta"],
        )
        threshold_summary = (
            f"A single tested upside ('{best['description'].lower()}') delivers enough overall movement "
            f"({best['score_delta']:+.2f} points) to cover the {gap:.2f}-point gap to {next_tier}."
        )
    elif needed_factor_points is not None and needed_factor_points > headroom:
        threshold_summary = (
            f"{label.capitalize()} is the strongest tested lever, but closing the full {gap:.2f}-point gap "
            f"through {label} alone would require about {needed_factor_points:.2f} points of sub-score lift, "
            f"which exceeds remaining headroom ({headroom:.2f}); multiple factors likely need to improve together."
        )
    elif max_lift_strongest < gap - 1e-6 and needed_factor_points is not None:
        threshold_summary = (
            f"{label.capitalize()} is the strongest tested lever, but closing the full {gap:.2f}-point gap "
            f"through {label} alone would require more overall movement than the best tested scenario "
            f"on that lever delivered ({max_lift_strongest:.2f} points)."
        )
    else:
        threshold_summary = (
            f"No single tested upside reaches the {gap:.2f}-point gap to {next_tier}; "
            f"a combined improvement across {label} and at least one other factor is likely required."
        )

    return {
        "next_tier": next_tier,
        "gap_overall_points": round(gap, 2),
        "strongest_single_factor_lever": strongest_lever,
        "estimated_factor_score_points_needed": needed_factor_points,
        "single_factor_upgrade_feasible": single_factor_upgrade_feasible,
        "threshold_summary": threshold_summary,
    }


def _build_risk_profile(
    features: dict,
    decision_result: dict,
    sensitivity: dict,
    intelligence: dict,
) -> dict:
    overall_risk_level = decision_result["risk_level"]
    sources: list[str] = []

    if features["competition_score"] < 45:
        sources.append("Competitive pressure is the dominant downside risk.")
    if features["margin_percent"] < 20:
        sources.append("Thin margin leaves little room for cost or price shocks.")
    if features["demand_score"] < 50:
        sources.append("Demand evidence is thin relative to preferred thresholds.")
    if features["review_score"] < 55:
        sources.append("Review evidence is directionally weak or limited in depth.")
    elif features["review_count"] < 50 and features["review_score"] >= 55:
        sources.append(
            "Review evidence is directionally positive but still limited in depth."
        )

    downside_changes = [
        s
        for s in sensitivity["scenarios"]
        if s["scenario_type"] == "downside" and s["decision_changed"]
    ]
    if downside_changes:
        sources.append(
            "At least one realistic downside scenario changes the recommendation."
        )

    hidden_fragility = False
    if overall_risk_level in ("LOW", "MEDIUM"):
        if any(s["decision_changed"] for s in sensitivity["scenarios"]):
            hidden_fragility = True
        downside_deltas = [
            s["score_delta"]
            for s in sensitivity["scenarios"]
            if s["scenario_type"] == "downside"
        ]
        if downside_deltas and min(downside_deltas) <= -6:
            hidden_fragility = True

    if not sources and overall_risk_level == "LOW":
        sources.append("No dominant structural risk flags surfaced in baseline signals.")

    return {
        "overall_risk_level": overall_risk_level,
        "risk_sources": sources[:5],
        "hidden_fragility": hidden_fragility,
    }


def _decision_posture(
    sensitivity: dict,
    risk_profile: dict,
    decision_gap: dict,
    decision: str,
) -> str:
    stability = sensitivity["decision_stability"]
    hidden = risk_profile["hidden_fragility"]
    gap = decision_gap.get("gap_to_next_tier")
    feasibility = decision_gap.get("feasibility")

    if stability == "ROBUST" and not any(
        s["decision_changed"] for s in sensitivity["scenarios"]
    ):
        return "ROBUST"
    if stability == "FRAGILE" or hidden:
        return "FRAGILE"
    if decision == "BUY" and stability != "ROBUST":
        return "CAUTIOUS"
    if gap is not None and feasibility == "NEAR" and decision != "BUY":
        return "OPPORTUNISTIC"
    return "CAUTIOUS"


def _calibrated_summary(
    decision: str,
    sensitivity: dict,
    intelligence: dict,
    risk_profile: dict,
    posture: str,
    confidence_breakdown: dict,
) -> str:
    stability = sensitivity["decision_stability"]
    worst = sensitivity["worst_case_decision"]
    path = intelligence.get("path_to_upgrade", "")
    counterfactuals_text = " ".join(intelligence.get("counterfactuals", []))
    weakest = confidence_breakdown["weakest_confidence_component"].replace("_", " ")

    if posture == "ROBUST":
        return (
            f"The recommendation appears robust because no tested scenario changes the decision "
            f"and score movement remains limited, supporting the baseline {decision} call."
        )
    if posture == "FRAGILE" and risk_profile["hidden_fragility"]:
        return (
            f"The baseline recommendation is {decision}, but the opportunity has hidden fragility: "
            f"stress scenarios can shift outcomes toward {worst}, so treat headline risk with caution."
        )
    if (
        "No tested upside scenario meaningfully improves" in path
        or "No tested upside scenario meaningfully improves" in counterfactuals_text
    ):
        return (
            f"The opportunity is viable but not resilient under tested upside levers; "
            f"no single tested improvement is sufficient to reach the next tier from {decision}. "
            f"Confidence is most constrained by {weakest}."
        )
    if stability == "MIXED":
        return (
            f"The baseline recommendation is {decision}, but sensitivity is mixed: "
            f"some realistic assumptions materially change the score or decision. "
            f"Confidence is most constrained by {weakest}."
        )
    recs = intelligence.get("recommendations") or []
    tail = recs[0] if recs else "validate key assumptions before scaling."
    return (
        f"The baseline recommendation is {decision} with {posture.lower()} posture; "
        f"{tail} Confidence is most constrained by {weakest}."
    )


def build_calibration_layer(
    features: dict,
    decision_result: dict,
    sensitivity: dict,
    intelligence: dict,
) -> dict:
    confidence_breakdown = _build_confidence_breakdown(
        features, decision_result, sensitivity
    )
    threshold_analysis = _build_threshold_analysis(
        features, decision_result, sensitivity, intelligence
    )
    risk_profile = _build_risk_profile(
        features, decision_result, sensitivity, intelligence
    )
    decision_gap = intelligence["decision_gap"]
    posture = _decision_posture(
        sensitivity, risk_profile, decision_gap, decision_result["decision"]
    )
    calibrated_summary = _calibrated_summary(
        decision_result["decision"],
        sensitivity,
        intelligence,
        risk_profile,
        posture,
        confidence_breakdown,
    )

    return {
        "confidence_breakdown": confidence_breakdown,
        "threshold_analysis": threshold_analysis,
        "risk_profile": risk_profile,
        "calibrated_summary": calibrated_summary,
        "decision_posture": posture,
    }
