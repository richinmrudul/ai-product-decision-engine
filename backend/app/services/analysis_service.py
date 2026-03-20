from app.schemas.analysis import ProductAnalysisRequest, ProductAnalysisResponse
from app.services.feature_engineering import compute_features
from app.services.decision_engine import build_decision_result
from app.services.explanation_engine import (
    build_reasons,
    build_warnings,
    build_summary,
    build_key_drivers,
)


def analyze_product(payload: ProductAnalysisRequest) -> ProductAnalysisResponse:
    features = compute_features(payload)
    decision_result = build_decision_result(features)

    reasons = build_reasons(features)
    warnings = build_warnings(features)
    summary = build_summary(
        decision_result["decision"],
        decision_result["risk_level"],
        decision_result["overall_score"],
    )
    key_drivers = build_key_drivers(features)

    return ProductAnalysisResponse(
        decision=decision_result["decision"],
        confidence_score=decision_result["confidence_score"],
        risk_level=decision_result["risk_level"],
        summary=summary,
        reasons=reasons,
        warnings=warnings,
        score_breakdown=decision_result["score_breakdown"],
        key_drivers=key_drivers,
        computed_features=features,
    )