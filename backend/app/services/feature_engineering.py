from app.schemas.analysis import ProductAnalysisRequest


def clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(value, max_value))


def compute_profitability_score(margin_percent: float) -> float:
    # Smooth curve with slower saturation.
    score = (margin_percent / (margin_percent + 30)) * 100
    return round(min(max(score, 0), 100), 2)


def compute_features(payload: ProductAnalysisRequest) -> dict:
    unit_profit = payload.price - payload.estimated_cost
    margin_percent = (unit_profit / payload.price * 100) if payload.price > 0 else 0

    # Demand proxy based on estimated monthly sales
    demand_score = clamp((payload.estimated_monthly_sales / 500) * 100, 0, 100)

    # Higher competition should reduce attractiveness
    competition_score = clamp(100 - (payload.competitor_count * 8), 0, 100)

    # Reviews combine average rating and review count
    rating_component = clamp((payload.average_rating / 5) * 70, 0, 70)
    review_volume_component = clamp((payload.review_count / 500) * 30, 0, 30)
    review_score = clamp(rating_component + review_volume_component, 0, 100)

    # Profitability score driven by margin % with slower saturation.
    profitability_score = compute_profitability_score(margin_percent)

    return {
        "unit_profit": round(unit_profit, 2),
        "margin_percent": round(margin_percent, 2),
        "demand_score": round(demand_score, 2),
        "competition_score": round(competition_score, 2),
        "review_score": round(review_score, 2),
        "profitability_score": round(profitability_score, 2),
    }