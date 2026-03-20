import type { ProductAnalysisResponse } from "@/lib/types";

type DecisionCardProps = {
  result: ProductAnalysisResponse;
};

export default function DecisionCard({ result }: DecisionCardProps) {
  return (
    <div className="mt-8 rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
      <h2 className="mb-2 text-3xl font-bold text-gray-900">
        Analysis Result
      </h2>

      <p className="mb-4 text-gray-600">{result.summary}</p>

      <div className="mb-6 grid grid-cols-1 gap-3 md:grid-cols-3">
        <div className="rounded-xl bg-gray-50 p-4">
          <p className="text-sm text-gray-500">Decision</p>
          <p className="text-xl font-semibold">{result.decision}</p>
        </div>
        <div className="rounded-xl bg-gray-50 p-4">
          <p className="text-sm text-gray-500">Confidence</p>
          <p className="text-xl font-semibold">{result.confidence_score}%</p>
        </div>
        <div className="rounded-xl bg-gray-50 p-4">
          <p className="text-sm text-gray-500">Risk Level</p>
          <p className="text-xl font-semibold">{result.risk_level}</p>
        </div>
      </div>

      <div className="mb-6">
        <h3 className="mb-2 text-lg font-semibold text-gray-900">Score Breakdown</h3>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {Object.entries(result.score_breakdown).map(([key, value]) => (
            <div key={key} className="rounded-xl border border-gray-200 p-4">
              <p className="text-sm capitalize text-gray-500">{key}</p>
              <p className="text-lg font-semibold">{value}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="mb-6">
        <h3 className="mb-2 text-lg font-semibold text-gray-900">Reasons</h3>
        <ul className="list-disc space-y-2 pl-5 text-gray-700">
          {result.reasons.map((reason, index) => (
            <li key={index}>{reason}</li>
          ))}
        </ul>
      </div>

      <div className="mb-6">
        <h3 className="mb-2 text-lg font-semibold text-gray-900">Warnings</h3>
        <ul className="list-disc space-y-2 pl-5 text-gray-700">
          {result.warnings.length > 0 ? (
            result.warnings.map((warning, index) => (
              <li key={index}>{warning}</li>
            ))
          ) : (
            <li>No major warnings detected.</li>
          )}
        </ul>
      </div>

      <div className="mb-6">
        <h3 className="mb-2 text-lg font-semibold text-gray-900">Key Drivers</h3>
        <div className="space-y-3">
          {result.key_drivers.map((driver, index) => (
            <div key={index} className="rounded-xl border border-gray-200 p-4">
              <p className="font-medium capitalize">
                {driver.factor} · {driver.impact}
              </p>
              <p className="text-sm text-gray-600">{driver.explanation}</p>
            </div>
          ))}
        </div>
      </div>

      <div>
        <h3 className="mb-2 text-lg font-semibold text-gray-900">Computed Features</h3>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {Object.entries(result.computed_features).map(([key, value]) => (
            <div key={key} className="rounded-xl border border-gray-200 p-4">
              <p className="text-sm capitalize text-gray-500">
                {key.replaceAll("_", " ")}
              </p>
              <p className="text-lg font-semibold">{value}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}