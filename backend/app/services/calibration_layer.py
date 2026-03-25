"""Deterministic calibration: explain confidence, risk posture, and top-level synthesis."""

from app.services.decision_engine import clamp


def _factor_spread(features: dict) -> float:
    scores = [
        features["profitability_score"],
        features["demand_score"],
        features["competition_score"],
        features["review_score"],
    ]
    return max(scores) - min(scores)


def _build_confidence_breakdown(features: dict, decision_result: dict, sensitivity: dict) -> dict:
    spread = _factor_spread(features)
    # High when factor scores are aligned; mirrors spread used in compute_confidence.
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

    final_confidence = decision_result["confidence_score"]

    return {
        "signal_consistency": signal_consistency,
        "data_support": data_support,
        "scenario_robustness": scenario_robustness,
        "final_confidence": final_confidence,
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
) -> str:
    stability = sensitivity["decision_stability"]
    worst = sensitivity["worst_case_decision"]
    path = intelligence.get("path_to_upgrade", "")
    counterfactuals_text = " ".join(intelligence.get("counterfactuals", []))

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
            f"no single tested improvement is sufficient to reach the next tier from {decision}."
        )
    if stability == "MIXED":
        return (
            f"The baseline recommendation is {decision}, but sensitivity is mixed: "
            f"some realistic assumptions materially change the score or decision."
        )
    recs = intelligence.get("recommendations") or []
    tail = recs[0] if recs else "validate key assumptions before scaling."
    return (
        f"The baseline recommendation is {decision} with {posture.lower()} posture; "
        f"{tail}"
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
    )

    return {
        "confidence_breakdown": confidence_breakdown,
        "risk_profile": risk_profile,
        "calibrated_summary": calibrated_summary,
        "decision_posture": posture,
    }
