def clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(value, max_value))


WEIGHTS = {
    "profitability": 0.35,
    "demand": 0.25,
    "competition": 0.20,
    "reviews": 0.20,
}


def compute_weighted_breakdown(features: dict) -> dict:
    return {
        "profitability": features["profitability_score"],
        "demand": features["demand_score"],
        "competition": features["competition_score"],
        "reviews": features["review_score"],
    }


def compute_overall_score(score_breakdown: dict) -> float:
    overall_score = (
        score_breakdown["profitability"] * WEIGHTS["profitability"]
        + score_breakdown["demand"] * WEIGHTS["demand"]
        + score_breakdown["competition"] * WEIGHTS["competition"]
        + score_breakdown["reviews"] * WEIGHTS["reviews"]
    )
    return round(overall_score, 2)


def decide(overall_score: float) -> str:
    if overall_score >= 75:
        return "BUY"
    if overall_score >= 55:
        return "WATCH"
    return "AVOID"


def compute_risk_level(features: dict) -> str:
    risk_points = 0

    if features["margin_percent"] < 20:
        risk_points += 1
    if features["demand_score"] < 50:
        risk_points += 1
    if features["competition_score"] < 45:
        risk_points += 1
    if features["review_score"] < 55:
        risk_points += 1

    if risk_points <= 1:
        return "LOW"
    if risk_points == 2:
        return "MEDIUM"
    return "HIGH"


def compute_confidence(overall_score: float, features: dict) -> float:
    spread = [
        features["profitability_score"],
        features["demand_score"],
        features["competition_score"],
        features["review_score"],
    ]

    consistency_penalty = (max(spread) - min(spread)) * 0.15
    confidence = overall_score - consistency_penalty

    return round(clamp(confidence, 35, 95), 2)


def build_decision_result(features: dict) -> dict:
    score_breakdown = compute_weighted_breakdown(features)
    overall_score = compute_overall_score(score_breakdown)
    decision = decide(overall_score)
    confidence_score = compute_confidence(overall_score, features)
    risk_level = compute_risk_level(features)

    score_breakdown["overall"] = overall_score

    return {
        "score_breakdown": score_breakdown,
        "overall_score": overall_score,
        "decision": decision,
        "confidence_score": confidence_score,
        "risk_level": risk_level,
    }