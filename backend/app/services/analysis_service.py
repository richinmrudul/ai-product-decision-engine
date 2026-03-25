from app.schemas.analysis import ProductAnalysisRequest, ProductAnalysisResponse
from app.services.decision_engine import build_decision_result
from app.services.explanation_engine import (
    build_reasons,
    build_warnings,
    build_summary,
    build_key_drivers,
)
from app.services.feature_engineering import compute_features
from app.services.calibration_layer import build_calibration_layer
from app.services.intelligence_layer import build_intelligence_layer
from app.services.scenario_engine import run_sensitivity_analysis
from app.services.search_engine import run_search_analysis


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
    sensitivity = run_sensitivity_analysis(payload)
    intelligence = build_intelligence_layer(features, decision_result, sensitivity)
    features_for_calibration = {**features, "review_count": payload.review_count}
    calibration = build_calibration_layer(
        features_for_calibration, decision_result, sensitivity, intelligence
    )
    calibrated_confidence = calibration["confidence_breakdown"]["final_confidence"]
    search_analysis = run_search_analysis(features, decision_result)

    return ProductAnalysisResponse(
        decision=decision_result["decision"],
        confidence_score=calibrated_confidence,
        risk_level=decision_result["risk_level"],
        summary=summary,
        reasons=reasons,
        warnings=warnings,
        score_breakdown=decision_result["score_breakdown"],
        key_drivers=key_drivers,
        computed_features=features,
        sensitivity=sensitivity,
        intelligence=intelligence,
        calibration=calibration,
        search_analysis=search_analysis,
    )