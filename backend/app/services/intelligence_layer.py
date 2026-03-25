"""Deterministic meta-analysis layer built on top of scoring and sensitivity."""

from app.services.decision_engine import WEIGHTS


def _sensitivity_level(score: float) -> str:
    if score < 45:
        return "HIGH"
    if score < 70:
        return "MEDIUM"
    return "LOW"


def _build_factor_sensitivity(features: dict) -> list[dict]:
    factor_map = [
        ("profitability", features["profitability_score"]),
        ("demand", features["demand_score"]),
        ("competition", features["competition_score"]),
        ("reviews", features["review_score"]),
    ]
    items = []
    for factor, score in factor_map:
        contribution = round(score * WEIGHTS[factor], 2)
        items.append(
            {
                "factor": factor,
                "score": round(score, 2),
                "weighted_contribution": contribution,
                "sensitivity_level": _sensitivity_level(score),
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


def _build_recommendations(features: dict, sensitivity: dict, decision_gap: dict) -> list[str]:
    recs: list[str] = []

    if features["margin_percent"] < 25:
        recs.append("Improve unit economics by negotiating costs or increasing price discipline.")
    if features["demand_score"] < 55:
        recs.append("Validate demand with focused tests before scaling inventory or ad spend.")
    if features["competition_score"] < 50:
        recs.append("Strengthen differentiation because competitive pressure is a key downside risk.")
    if features["review_score"] < 60:
        recs.append("Increase review quality and volume to improve conversion confidence.")

    if sensitivity["decision_stability"] != "ROBUST":
        recs.append(
            "Prioritize mitigation for the most sensitive scenario to reduce decision volatility."
        )

    if decision_gap["gap_to_next_tier"] <= 5 and decision_gap["gap_to_next_tier"] > 0:
        recs.append(
            f"The product is close to {decision_gap['next_decision_tier']}; targeted optimizations could bridge the remaining score gap."
        )

    if not recs:
        recs.append("Maintain current operating assumptions and monitor key signals monthly.")

    return recs[:4]


def _build_uncertainty_flags(features: dict) -> list[str]:
    flags: list[str] = []
    if features["review_score"] < 55:
        flags.append("Limited or low-quality reviews increase confidence uncertainty.")
    if features["demand_score"] < 50:
        flags.append("Demand signal is weak and could be unstable outside current assumptions.")
    if features["competition_score"] < 45:
        flags.append("High competitive intensity may compress achievable performance.")
    return flags


def build_intelligence_layer(features: dict, decision_result: dict, sensitivity: dict) -> dict:
    factor_sensitivity = _build_factor_sensitivity(features)
    decision_gap = _build_decision_gap(
        overall_score=decision_result["overall_score"],
        decision=decision_result["decision"],
    )
    recommendations = _build_recommendations(features, sensitivity, decision_gap)
    uncertainty_flags = _build_uncertainty_flags(features)

    return {
        "factor_sensitivity": factor_sensitivity,
        "decision_gap": decision_gap,
        "recommendations": recommendations,
        "uncertainty_flags": uncertainty_flags,
    }
