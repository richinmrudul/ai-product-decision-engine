from app.schemas.analysis import ProductAnalysisRequest, ProductAnalysisResponse


def analyze_product(payload: ProductAnalysisRequest) -> ProductAnalysisResponse:
    return ProductAnalysisResponse(
        decision="WATCH",
        confidence_score=72.5,
        risk_level="MEDIUM",
        reasons=[
            "Estimated margin looks promising",
            "Demand appears stable",
            "Competition is present but not overwhelming",
        ],
        warnings=[
            "Review count is relatively low",
            "Sales estimate may be uncertain",
        ],
    )