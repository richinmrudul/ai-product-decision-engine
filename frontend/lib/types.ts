export type ProductAnalysisRequest = {
  product_name: string;
  price: number;
  estimated_cost: number;
  estimated_monthly_sales: number;
  average_rating: number;
  review_count: number;
  competitor_count: number;
};

export type KeyDriver = {
  factor: string;
  impact: string;
  explanation: string;
};

export type ProductAnalysisResponse = {
  decision: string;
  confidence_score: number;
  risk_level: string;
  summary: string;
  reasons: string[];
  warnings: string[];
  score_breakdown: Record<string, number>;
  key_drivers: KeyDriver[];
  computed_features: Record<string, number>;
};