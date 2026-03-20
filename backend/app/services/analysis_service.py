from app.schemas.analysis import ProductAnalysisRequest, ProductAnalysisResponse
from app.services.feature_engineering import compute_features
from app.services.decision_engine import (
    compute_overall_score,
    decide,
    compute_risk_level,
    compute_confidence,
)
from app.services.explanation_engine import (
    build_reasons,
    build_warnings,
    build_summary,
    build_key_drivers,
)


def analyze_product(payload: ProductAnalysisRequest) -> ProductAnalysisResponse:
    features = compute_features(payload)

    overall_score, score_breakdown = compute_overall_score(features)
    decision = decide(overall_score)
    risk_level = compute_risk_level(features)
    confidence_score = compute_confidence(overall_score, features)

    reasons = build_reasons(features)
    warnings = build_warnings(features)
    summary = build_summary(decision, risk_level, features)
    key_drivers = build_key_drivers(features)

    return ProductAnalysisResponse(
        decision=decision,
        confidence_score=confidence_score,
        risk_level=risk_level,
        summary=summary,
        reasons=reasons,
        warnings=warnings,
        score_breakdown=score_breakdown,
        key_drivers=key_drivers,
        computed_features=features,
    )