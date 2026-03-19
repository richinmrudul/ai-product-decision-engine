from fastapi import APIRouter

from app.schemas.analysis import ProductAnalysisRequest, ProductAnalysisResponse
from app.services.analysis_service import analyze_product

router = APIRouter()


@router.post("/analyze", response_model=ProductAnalysisResponse)
def analyze(payload: ProductAnalysisRequest):
    return analyze_product(payload)