import type { ProductAnalysisResponse } from "@/lib/types";

type DecisionCardProps = {
  result: ProductAnalysisResponse;
};

export default function DecisionCard({ result }: DecisionCardProps) {
  const scoreItems: Array<{ key: string; label: string; value: number }> = [
    {
      key: "profitability",
      label: "Profitability",
      value: result.score_breakdown.profitability,
    },
    { key: "demand", label: "Demand", value: result.score_breakdown.demand },
    {
      key: "competition",
      label: "Competition",
      value: result.score_breakdown.competition,
    },
    { key: "reviews", label: "Reviews", value: result.score_breakdown.reviews },
    { key: "overall", label: "Overall", value: result.score_breakdown.overall },
  ];

  return (
    <section className="w-full max-w-4xl rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
      <header className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Analysis Result</h2>
        <p className="mt-2 text-gray-600">{result.summary}</p>
      </header>

      <div className="mb-6 grid grid-cols-1 gap-3 md:grid-cols-3">
        <div className="rounded-xl border border-gray-200 bg-gray-50 p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-gray-500">
            Decision
          </p>
          <p className="mt-1 text-2xl font-semibold text-gray-900">
            {result.decision}
          </p>
        </div>
        <div className="rounded-xl border border-gray-200 bg-gray-50 p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-gray-500">
            Confidence
          </p>
          <p className="mt-1 text-2xl font-semibold text-gray-900">
            {result.confidence_score.toFixed(2)}%
          </p>
        </div>
        <div className="rounded-xl border border-gray-200 bg-gray-50 p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-gray-500">
            Risk Level
          </p>
          <p className="mt-1 text-2xl font-semibold text-gray-900">
            {result.risk_level}
          </p>
        </div>
      </div>

      <div className="mb-6">
        <h3 className="mb-2 text-lg font-semibold text-gray-900">
          Score Breakdown
        </h3>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {scoreItems.map((item) => (
            <div key={item.key} className="rounded-xl border border-gray-200 p-4">
              <p className="text-sm text-gray-500">{item.label}</p>
              <p className="text-lg font-semibold text-gray-900">
                {item.value.toFixed(2)}
              </p>
            </div>
          ))}
        </div>
      </div>

      <div className="mb-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div>
          <h3 className="mb-2 text-lg font-semibold text-gray-900">Reasons</h3>
          <ul className="list-disc space-y-2 pl-5 text-gray-700">
            {result.reasons.map((reason, index) => (
              <li key={`reason-${index}`}>{reason}</li>
            ))}
          </ul>
        </div>
        <div>
          <h3 className="mb-2 text-lg font-semibold text-gray-900">Warnings</h3>
          {result.warnings.length > 0 ? (
            <ul className="list-disc space-y-2 pl-5 text-gray-700">
              {result.warnings.map((warning, index) => (
                <li key={`warning-${index}`}>{warning}</li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-gray-600">No major warnings detected.</p>
          )}
        </div>
      </div>

      <div className="mb-6">
        <h3 className="mb-2 text-lg font-semibold text-gray-900">Key Drivers</h3>
        {result.key_drivers.length > 0 ? (
          <div className="space-y-3">
            {result.key_drivers.map((driver, index) => (
              <div
                key={`driver-${index}`}
                className="rounded-xl border border-gray-200 p-4"
              >
                <p className="font-medium capitalize text-gray-900">
                  {driver.factor}{" "}
                  <span
                    className={
                      driver.impact === "positive"
                        ? "text-emerald-700"
                        : "text-rose-700"
                    }
                  >
                    ({driver.impact})
                  </span>
                </p>
                <p className="mt-1 text-sm text-gray-600">{driver.explanation}</p>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-600">
            No strong positive or negative drivers identified.
          </p>
        )}
      </div>

      <div className="mb-6 rounded-xl border border-gray-200 bg-slate-50/80 p-5">
        <h3 className="mb-1 text-lg font-semibold text-gray-900">
          Sensitivity analysis
        </h3>
        <p className="mb-4 text-sm text-gray-600">
          Stress tests vs your baseline (same pipeline, adjusted assumptions).
        </p>
        <div className="mb-4 flex flex-wrap gap-3">
          <div className="rounded-lg border border-gray-200 bg-white px-4 py-2">
            <p className="text-xs font-medium uppercase tracking-wide text-gray-500">
              Decision stability
            </p>
            <p className="text-lg font-semibold text-gray-900">
              {result.sensitivity.decision_stability}
            </p>
          </div>
          <div className="rounded-lg border border-gray-200 bg-white px-4 py-2">
            <p className="text-xs font-medium uppercase tracking-wide text-gray-500">
              Worst case
            </p>
            <p className="text-lg font-semibold text-gray-900">
              {result.sensitivity.worst_case_decision}
            </p>
          </div>
          <div className="rounded-lg border border-gray-200 bg-white px-4 py-2">
            <p className="text-xs font-medium uppercase tracking-wide text-gray-500">
              Best case
            </p>
            <p className="text-lg font-semibold text-gray-900">
              {result.sensitivity.best_case_decision}
            </p>
          </div>
        </div>
        <ul className="space-y-3">
          {result.sensitivity.scenarios.map((s) => (
            <li
              key={s.scenario_id}
              className="rounded-lg border border-gray-200 bg-white p-4"
            >
              <p className="font-medium text-gray-900">{s.description}</p>
              <p className="mt-1 text-sm text-gray-600">
                Decision:{" "}
                <span className="font-semibold text-gray-900">{s.decision}</span>
                {" · "}
                Score: {s.overall_score.toFixed(2)}
                {" · "}
                Risk: {s.risk_level}
              </p>
            </li>
          ))}
        </ul>
      </div>

      <div>
        <h3 className="mb-2 text-lg font-semibold text-gray-900">
          Computed Features
        </h3>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {Object.entries(result.computed_features).map(([key, value]) => (
            <div key={key} className="rounded-xl border border-gray-200 p-4">
              <p className="text-sm capitalize text-gray-500">
                {key.replaceAll("_", " ")}
              </p>
              <p className="text-lg font-semibold text-gray-900">
                {value.toFixed(2)}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}