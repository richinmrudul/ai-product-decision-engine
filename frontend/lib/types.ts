export type ProductAnalysisRequest = {
  product_name: string;
  price: number;
  estimated_cost: number;
  estimated_monthly_sales: number;
  average_rating: number;
  review_count: number;
  competitor_count: number;
};

export type DriverImpact = "positive" | "negative";

export type KeyDriver = {
  factor: "profitability" | "demand" | "competition" | "reviews";
  impact: DriverImpact;
  explanation: string;
};

export type ScoreBreakdown = {
  profitability: number;
  demand: number;
  competition: number;
  reviews: number;
  overall: number;
};

export type ScenarioOutcome = {
  scenario_id: string;
  description: string;
  decision: string;
  overall_score: number;
  risk_level: string;
};

export type SensitivityAnalysis = {
  scenarios: ScenarioOutcome[];
  decision_stability: string;
  worst_case_decision: string;
  best_case_decision: string;
};

export type ProductAnalysisResponse = {
  decision: string;
  confidence_score: number;
  risk_level: string;
  summary: string;
  reasons: string[];
  warnings: string[];
  score_breakdown: ScoreBreakdown;
  key_drivers: KeyDriver[];
  computed_features: Record<string, number>;
  sensitivity: SensitivityAnalysis;
};