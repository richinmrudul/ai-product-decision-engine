"use client";

import { useState } from "react";

import DecisionCard from "@/components/DecisionCard";
import ProductAnalysisForm from "@/components/ProductAnalysisForm";
import { analyzeProduct } from "@/lib/api";
import type { ProductAnalysisRequest, ProductAnalysisResponse } from "@/lib/types";

export default function Home() {
  const [result, setResult] = useState<ProductAnalysisResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleAnalyze(payload: ProductAnalysisRequest) {
    setIsLoading(true);
    setError(null);

    try {
      const data = await analyzeProduct(payload);
      setResult(data);
    } catch {
      setResult(null);
      setError("Could not reach backend. Make sure FastAPI is running.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-gray-50 px-4 py-10">
      <div className="mx-auto flex max-w-4xl flex-col items-center gap-6">
        <h1 className="text-center text-3xl font-bold text-gray-900">
          AI Product Decision Engine
        </h1>

        <ProductAnalysisForm onSubmit={handleAnalyze} isLoading={isLoading} />

        {error ? (
          <p className="w-full max-w-2xl rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </p>
        ) : null}

        {result ? <DecisionCard result={result} /> : null}
      </div>
    </main>
  );
}