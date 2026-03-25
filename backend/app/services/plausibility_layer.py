"""Deterministic input plausibility checks (no ML)."""

from app.schemas.analysis import ProductAnalysisRequest


def _clamp_score(score: float) -> float:
    return max(0.0, min(100.0, score))


def build_plausibility_layer(payload: ProductAnalysisRequest, features: dict) -> dict:
    score = 100.0
    extreme: list[str] = []
    warnings: list[str] = []
    suspicious: list[str] = []

    price = payload.price
    cost = payload.estimated_cost
    sales = payload.estimated_monthly_sales
    rating = payload.average_rating
    reviews = payload.review_count
    competitors = payload.competitor_count

    margin = features["margin_percent"]
    unit_profit = features["unit_profit"]
    demand_score = features["demand_score"]
    review_score = features["review_score"]

    if price <= 0:
        extreme.append("non_positive_price")
        score -= 55
        warnings.append("Price must be positive for meaningful unit economics; outputs are not reliable.")
    elif price > 500_000:
        extreme.append("extremely_high_price")
        score -= 35
        warnings.append("Price is far outside typical product ranges; scoring may not reflect real markets.")
    elif price > 50_000:
        extreme.append("very_high_price")
        score -= 18
        warnings.append("Price is unusually high; treat profitability signals as stylized.")

    if cost < 0:
        extreme.append("negative_cost")
        score -= 45
        warnings.append("Negative cost is invalid; profitability is not trustworthy.")
    elif cost > price > 0:
        extreme.append("cost_exceeds_price")
        score -= 35
        warnings.append("Cost exceeds price, so margin is negative or undefined in a realistic listing.")

    if price > 0 and cost >= 0 and cost <= price:
        if cost > 0:
            price_cost_ratio = price / cost
            if price_cost_ratio > 1_000:
                suspicious.append("implausible_price_to_cost_ratio")
                score -= 28
                warnings.append(
                    "Price is orders of magnitude above cost; this pattern often indicates bad or adversarial inputs."
                )
            elif price_cost_ratio > 200:
                suspicious.append("very_high_price_to_cost_ratio")
                score -= 12
        if cost == 0 and price > 1000:
            suspicious.append("zero_cost_with_high_price")
            score -= 22
            warnings.append("Zero cost with a high price implies unrealistic margin; results are inflated.")

    if abs(unit_profit) > 0 and price > 0 and abs(unit_profit) > price * 0.999:
        extreme.append("absurd_unit_profit_vs_price")
        score -= 25
        warnings.append("Unit profit is implausibly large relative to price.")

    if margin > 92 and demand_score < 35 and sales < 30:
        suspicious.append("extreme_margin_with_tiny_demand")
        score -= 20
        warnings.append("Sky-high margin combined with very weak demand evidence is an unusual combination.")

    if margin > 90 and review_score < 40 and reviews < 15:
        suspicious.append("extreme_margin_with_weak_review_signal")
        score -= 15
        warnings.append("Very high margin with weak review quality/volume may not reflect a real launch.")

    if price > 50_000 and cost < 5:
        extreme.append("adversarial_price_vs_tiny_cost")
        score -= 40
        warnings.append("Huge price with negligible cost mimics adversarial inputs; distrust headline scores.")

    if sales > 2_000_000:
        extreme.append("extremely_high_monthly_sales")
        score -= 22
        warnings.append("Monthly sales are unrealistically large for most SKU-level estimates.")

    if sales < 0:
        extreme.append("negative_monthly_sales")
        score -= 30

    if rating < 0 or rating > 5:
        extreme.append("rating_out_of_valid_range")
        score -= 30
        warnings.append("Average rating must be between 0 and 5.")

    if reviews < 0:
        extreme.append("negative_review_count")
        score -= 25

    if competitors < 0:
        extreme.append("negative_competitor_count")
        score -= 20

    if price > 0 and 0 < cost < 0.01 and price > 100:
        suspicious.append("near_zero_cost_high_price")
        score -= 18
        warnings.append("Near-zero cost with a large price inflates margin; verify sourcing numbers.")

    score = _clamp_score(score)

    if score >= 75:
        risk = "LOW"
    elif score >= 45:
        risk = "MEDIUM"
    else:
        risk = "HIGH"

    return {
        "input_plausibility_score": round(score, 2),
        "extreme_value_flags": extreme,
        "plausibility_warnings": warnings,
        "suspicious_combination_flags": suspicious,
        "outlier_risk_level": risk,
    }


def apply_plausibility_to_confidence(base_confidence: float, plausibility: dict) -> float:
    """Deterministically down-weight confidence when inputs look unrealistic."""
    p = plausibility["input_plausibility_score"] / 100.0
    risk = plausibility["outlier_risk_level"]
    if risk == "HIGH":
        factor = 0.42 + 0.58 * p
    elif risk == "MEDIUM":
        factor = 0.82 + 0.18 * p
    else:
        factor = 1.0
    return round(max(35.0, min(95.0, base_confidence * factor)), 2)


def append_plausibility_to_calibration(calibration: dict, plausibility: dict) -> None:
    """Mutates calibration: adjusts final_confidence and extends calibrated_summary."""
    cb = calibration["confidence_breakdown"]
    base = cb["final_confidence"]
    adjusted = apply_plausibility_to_confidence(base, plausibility)
    cb["final_confidence"] = adjusted

    risk = plausibility["outlier_risk_level"]
    if risk != "LOW":
        cb["confidence_explanation"] = (
            cb["confidence_explanation"]
            + f" After input plausibility ({plausibility['input_plausibility_score']:.0f}/100, "
            f"outlier risk {risk}), final confidence is adjusted from {base:.2f} to {adjusted:.2f}."
        )

    if risk == "HIGH":
        calibration["calibrated_summary"] = (
            calibration["calibrated_summary"]
            + " Input quality is suspect: treat the recommendation as illustrative, not actionable, until inputs are normalized."
        )
    elif risk == "MEDIUM":
        calibration["calibrated_summary"] = (
            calibration["calibrated_summary"]
            + " Some inputs look stretched; reduce trust in the headline score until assumptions are validated."
        )
