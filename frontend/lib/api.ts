import type { ProductAnalysisRequest, ProductAnalysisResponse } from "@/lib/types";

const ANALYZE_URL = "http://127.0.0.1:8000/api/v1/analyze";

export async function analyzeProduct(
  payload: ProductAnalysisRequest
): Promise<ProductAnalysisResponse> {
  const response = await fetch(ANALYZE_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error("Failed to analyze product");
  }

  return response.json();
}
