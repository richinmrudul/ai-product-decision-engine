export type ProductAnalysisRequest = {
  product_name: string;
  price: number;
  estimated_cost: number;
  estimated_monthly_sales: number;
  average_rating: number;
  review_count: number;
  competitor_count: number;
};

export type ProductAnalysisResponse = {
  decision: string;
  confidence_score: number;
  risk_level: string;
  reasons: string[];
  warnings: string[];
};
