def build_reasons(features: dict) -> list[str]:
    reasons = []

    if features["margin_percent"] >= 30:
        reasons.append("The product has a strong projected margin profile.")
    if features["demand_score"] >= 65:
        reasons.append("Estimated monthly sales suggest healthy demand.")
    if features["competition_score"] >= 60:
        reasons.append("Competitive pressure appears manageable.")
    if features["review_score"] >= 70:
        reasons.append("Review quality and volume support product credibility.")

    if not reasons:
        reasons.append("The product shows at least one promising signal, but not enough to stand out strongly.")

    return reasons


def build_warnings(features: dict) -> list[str]:
    warnings = []

    if features["margin_percent"] < 20:
        warnings.append("Projected margin is thin, which reduces room for error.")
    if features["demand_score"] < 50:
        warnings.append("Estimated demand appears limited relative to preferred thresholds.")
    if features["competition_score"] < 45:
        warnings.append("Competition appears high, which may make differentiation difficult.")
    if features["review_score"] < 55:
        warnings.append("Review quality or review volume is weak, which increases uncertainty.")

    return warnings


def build_summary(decision: str, risk_level: str, features: dict) -> str:
    if decision == "BUY":
        return (
            f"This product appears attractive overall, with strong upside across key signals. "
            f"Risk is currently assessed as {risk_level.lower()}."
        )

    if decision == "WATCH":
        return (
            f"This product shows some promising traits, but the opportunity is mixed. "
            f"Risk is currently assessed as {risk_level.lower()}, so closer monitoring is recommended."
        )

    return (
        f"This product currently looks unattractive based on the available signals. "
        f"Risk is assessed as {risk_level.lower()}, and the opportunity may need major improvement."
    )


def build_key_drivers(features: dict) -> list[dict]:
    drivers = []

    if features["profitability_score"] >= 70:
        drivers.append({
            "factor": "profitability",
            "impact": "positive",
            "explanation": "Projected margin remains above the preferred threshold."
        })
    elif features["profitability_score"] < 50:
        drivers.append({
            "factor": "profitability",
            "impact": "negative",
            "explanation": "Projected margin is weaker than the preferred range."
        })

    if features["demand_score"] >= 65:
        drivers.append({
            "factor": "demand",
            "impact": "positive",
            "explanation": "Estimated monthly sales indicate stronger demand."
        })
    elif features["demand_score"] < 50:
        drivers.append({
            "factor": "demand",
            "impact": "negative",
            "explanation": "Estimated monthly sales indicate weaker demand."
        })

    if features["competition_score"] >= 60:
        drivers.append({
            "factor": "competition",
            "impact": "positive",
            "explanation": "Competitive pressure appears manageable."
        })
    elif features["competition_score"] < 45:
        drivers.append({
            "factor": "competition",
            "impact": "negative",
            "explanation": "Competitive pressure appears elevated."
        })

    if features["review_score"] >= 70:
        drivers.append({
            "factor": "reviews",
            "impact": "positive",
            "explanation": "Review quality and volume increase confidence in the opportunity."
        })
    elif features["review_score"] < 55:
        drivers.append({
            "factor": "reviews",
            "impact": "negative",
            "explanation": "Weak review strength increases uncertainty."
        })

    return drivers