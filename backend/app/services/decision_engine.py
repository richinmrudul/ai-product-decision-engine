def clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(value, max_value))


def compute_overall_score(features: dict) -> tuple[float, dict]:
    score_breakdown = {
        "profitability": features["profitability_score"],
        "demand": features["demand_score"],
        "competition": features["competition_score"],
        "reviews": features["review_score"],
    }

    overall_score = (
        score_breakdown["profitability"] * 0.35
        + score_breakdown["demand"] * 0.25
        + score_breakdown["competition"] * 0.20
        + score_breakdown["reviews"] * 0.20
    )

    return round(overall_score, 2), {
        key: round(value, 2) for key, value in score_breakdown.items()
    }


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