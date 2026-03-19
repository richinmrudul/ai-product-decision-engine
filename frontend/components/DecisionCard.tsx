import type { ProductAnalysisResponse } from "@/lib/types";

type DecisionCardProps = {
  result: ProductAnalysisResponse;
};

export default function DecisionCard({ result }: DecisionCardProps) {
  return (
    <section className="w-full max-w-2xl rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
      <h2 className="text-xl font-semibold text-gray-900">Analysis Result</h2>

      <div className="mt-4 grid grid-cols-1 gap-3 text-sm text-gray-700 sm:grid-cols-3">
        <p>
          <span className="font-medium">Decision:</span> {result.decision}
        </p>
        <p>
          <span className="font-medium">Confidence:</span>{" "}
          {result.confidence_score}%
        </p>
        <p>
          <span className="font-medium">Risk:</span> {result.risk_level}
        </p>
      </div>

      <div className="mt-4">
        <h3 className="text-sm font-semibold text-gray-900">Reasons</h3>
        <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-gray-700">
          {result.reasons.map((reason) => (
            <li key={reason}>{reason}</li>
          ))}
        </ul>
      </div>

      <div className="mt-4">
        <h3 className="text-sm font-semibold text-gray-900">Warnings</h3>
        <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-gray-700">
          {result.warnings.map((warning) => (
            <li key={warning}>{warning}</li>
          ))}
        </ul>
      </div>
    </section>
  );
}
