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
    direction: str
    decision: str
    overall_score: float
    score_delta: float
    decision_changed: bool
    risk_level: str


class RobustnessSummary(BaseModel):
    robustness_level: str
    most_sensitive_factor: str
    largest_downside_delta: float
    largest_upside_delta: float
    baseline_decision_retained_in_downside: bool


class SensitivityAnalysis(BaseModel):
    scenarios: List[ScenarioOutcome]
    decision_stability: str
    worst_case_decision: str
    best_case_decision: str
    robustness_summary: RobustnessSummary


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