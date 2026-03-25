from typing import List, Dict
from pydantic import BaseModel


class ProductAnalysisRequest(BaseModel):
    product_name: str
    price: float
    estimated_cost: float
    estimated_monthly_sales: int
    average_rating: float
    review_count: int
    competitor_count: int


class KeyDriver(BaseModel):
    factor: str
    impact: str
    explanation: str


class ScenarioOutcome(BaseModel):
    scenario_id: str
    description: str
    scenario_type: str
    decision: str
    overall_score: float
    score_delta: float
    decision_changed: bool
    risk_level: str
    impact_direction: str


class SensitivityAnalysis(BaseModel):
    scenarios: List[ScenarioOutcome]
    decision_stability: str
    worst_case_decision: str
    best_case_decision: str
    most_sensitive_scenario: str
    largest_score_drop: float
    largest_score_gain: float
    robustness_summary: str


class FactorSensitivity(BaseModel):
    factor: str
    score: float
    weighted_contribution: float
    sensitivity_level: str


class DecisionGap(BaseModel):
    current_score: float
    next_decision_tier: str
    gap_to_next_tier: float


class ProductIntelligence(BaseModel):
    factor_sensitivity: List[FactorSensitivity]
    decision_gap: DecisionGap
    recommendations: List[str]
    uncertainty_flags: List[str]


class ProductAnalysisResponse(BaseModel):
    decision: str
    confidence_score: float
    risk_level: str
    summary: str
    reasons: List[str]
    warnings: List[str]
    score_breakdown: Dict[str, float]
    key_drivers: List[KeyDriver]
    computed_features: Dict[str, float]
    sensitivity: SensitivityAnalysis
    intelligence: ProductIntelligence