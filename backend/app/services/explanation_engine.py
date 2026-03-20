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


def build_summary(decision: str, risk_level: str, overall_score: float) -> str:
    if decision == "BUY":
        return (
            f"This product appears attractive overall, with strong upside across key signals. "
            f"Overall score is {overall_score}, and risk is {risk_level.lower()}."
        )

    if decision == "WATCH":
        return (
            f"This product shows some promising traits, but the opportunity is mixed. "
            f"Overall score is {overall_score}, with {risk_level.lower()} risk, so closer monitoring is recommended."
        )

    return (
        f"This product currently looks unattractive based on the available signals. "
        f"Overall score is {overall_score}, risk is {risk_level.lower()}, and the opportunity may need major improvement."
    )


def _driver_explanation(factor: str, impact: str) -> str:
    if factor == "profitability":
        return (
            "Projected margin remains above target thresholds."
            if impact == "positive"
            else "Projected margin is below preferred thresholds."
        )
    if factor == "demand":
        return (
            "Estimated monthly sales suggest healthy demand."
            if impact == "positive"
            else "Estimated monthly sales suggest weak demand."
        )
    if factor == "competition":
        return (
            "Competitive pressure appears manageable."
            if impact == "positive"
            else "Competitive pressure appears elevated."
        )
    return (
        "Review quality and volume support product confidence."
        if impact == "positive"
        else "Review quality or volume is weak, increasing uncertainty."
    )


def build_key_drivers(features: dict) -> list[dict]:
    factors = [
        ("profitability", features["profitability_score"]),
        ("demand", features["demand_score"]),
        ("competition", features["competition_score"]),
        ("reviews", features["review_score"]),
    ]
    drivers = []
    for factor, score in factors:
        if score >= 70:
            impact = "positive"
        elif score < 45:
            impact = "negative"
        else:
            continue

        drivers.append({
            "factor": factor,
            "impact": impact,
            "explanation": _driver_explanation(factor, impact),
        })

    return drivers