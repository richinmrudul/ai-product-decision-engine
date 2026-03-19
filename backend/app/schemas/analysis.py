from typing import List
from pydantic import BaseModel


class ProductAnalysisRequest(BaseModel):
    product_name: str
    price: float
    estimated_cost: float
    estimated_monthly_sales: int
    average_rating: float
    review_count: int
    competitor_count: int


class ProductAnalysisResponse(BaseModel):
    decision: str
    confidence_score: float
    risk_level: str
    reasons: List[str]
    warnings: List[str]