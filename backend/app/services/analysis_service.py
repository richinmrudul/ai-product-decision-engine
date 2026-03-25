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
from app.services.plausibility_layer import (
    append_plausibility_to_calibration,
    append_validity_to_calibrated_summary,
    apply_search_solver_gating,
    build_plausibility_layer,
    compute_recommendation_gate,
    prepend_invalidity_to_summary,
)
from app.services.scenario_engine import run_sensitivity_analysis
from app.services.search_engine import run_search_analysis
from app.services.solver_engine import run_solver_analysis


def analyze_product(payload: ProductAnalysisRequest) -> ProductAnalysisResponse:
    features = compute_features(payload)
    plausibility = build_plausibility_layer(payload, features)
    gate = compute_recommendation_gate(plausibility)
    decision_result = build_decision_result(features)

    reasons = build_reasons(features)
    warnings = build_warnings(features)
    if plausibility["plausibility_warnings"]:
        warnings = warnings + plausibility["plausibility_warnings"][:4]
    summary = prepend_invalidity_to_summary(
        build_summary(
            decision_result["decision"],
            decision_result["risk_level"],
            decision_result["overall_score"],
        ),
        gate,
    )
    key_drivers = build_key_drivers(features)
    sensitivity = run_sensitivity_analysis(payload)
    intelligence = build_intelligence_layer(features, decision_result, sensitivity)
    if plausibility["outlier_risk_level"] == "HIGH":
        intelligence["uncertainty_flags"] = list(intelligence["uncertainty_flags"]) + [
            "Input plausibility is low; treat scores and recommendations as non-executable until inputs are normalized.",
        ]
    elif plausibility["outlier_risk_level"] == "MEDIUM":
        intelligence["uncertainty_flags"] = list(intelligence["uncertainty_flags"]) + [
            "Some inputs look stretched; validate assumptions before relying on the headline decision.",
        ]

    features_for_calibration = {**features, "review_count": payload.review_count}
    calibration = build_calibration_layer(
        features_for_calibration, decision_result, sensitivity, intelligence
    )
    append_plausibility_to_calibration(calibration, plausibility)
    append_validity_to_calibrated_summary(calibration, gate)
    calibrated_confidence = calibration["confidence_breakdown"]["final_confidence"]

    search_analysis = run_search_analysis(features, decision_result)
    solver_analysis = run_solver_analysis(
        features, decision_result, sensitivity, intelligence
    )
    search_analysis, solver_analysis = apply_search_solver_gating(
        search_analysis, solver_analysis, gate
    )

    return ProductAnalysisResponse(
        decision=decision_result["decision"],
        confidence_score=calibrated_confidence,
        risk_level=decision_result["risk_level"],
        recommendation_validity=gate["recommendation_validity"],
        actionability=gate["actionability"],
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
        solver_analysis=solver_analysis,
        plausibility=plausibility,
    )
