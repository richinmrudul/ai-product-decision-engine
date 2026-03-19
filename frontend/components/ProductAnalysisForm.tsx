import { useState } from "react";

import type { ProductAnalysisRequest } from "@/lib/types";

type ProductAnalysisFormProps = {
  onSubmit: (payload: ProductAnalysisRequest) => Promise<void>;
  isLoading: boolean;
};

const initialForm: ProductAnalysisRequest = {
  product_name: "",
  price: 0,
  estimated_cost: 0,
  estimated_monthly_sales: 0,
  average_rating: 0,
  review_count: 0,
  competitor_count: 0,
};

export default function ProductAnalysisForm({
  onSubmit,
  isLoading,
}: ProductAnalysisFormProps) {
  const [formData, setFormData] = useState<ProductAnalysisRequest>(initialForm);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onSubmit(formData);
  }

  function updateField<K extends keyof ProductAnalysisRequest>(
    field: K,
    value: ProductAnalysisRequest[K]
  ) {
    setFormData((prev) => ({
      ...prev,
      [field]: value,
    }));
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="w-full max-w-2xl space-y-4 rounded-lg border border-gray-200 bg-white p-6 shadow-sm"
    >
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">
          Product Name
        </label>
        <input
          required
          type="text"
          value={formData.product_name}
          onChange={(event) => updateField("product_name", event.target.value)}
          className="w-full rounded-md border border-gray-300 px-3 py-2 outline-none focus:border-gray-500"
        />
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">
            Price
          </label>
          <input
            type="number"
            min="0"
            step="0.01"
            value={formData.price}
            onChange={(event) => updateField("price", Number(event.target.value))}
            className="w-full rounded-md border border-gray-300 px-3 py-2 outline-none focus:border-gray-500"
          />
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">
            Estimated Cost
          </label>
          <input
            type="number"
            min="0"
            step="0.01"
            value={formData.estimated_cost}
            onChange={(event) =>
              updateField("estimated_cost", Number(event.target.value))
            }
            className="w-full rounded-md border border-gray-300 px-3 py-2 outline-none focus:border-gray-500"
          />
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">
            Estimated Monthly Sales
          </label>
          <input
            type="number"
            min="0"
            step="1"
            value={formData.estimated_monthly_sales}
            onChange={(event) =>
              updateField("estimated_monthly_sales", Number(event.target.value))
            }
            className="w-full rounded-md border border-gray-300 px-3 py-2 outline-none focus:border-gray-500"
          />
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">
            Average Rating
          </label>
          <input
            type="number"
            min="0"
            max="5"
            step="0.1"
            value={formData.average_rating}
            onChange={(event) =>
              updateField("average_rating", Number(event.target.value))
            }
            className="w-full rounded-md border border-gray-300 px-3 py-2 outline-none focus:border-gray-500"
          />
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">
            Review Count
          </label>
          <input
            type="number"
            min="0"
            step="1"
            value={formData.review_count}
            onChange={(event) =>
              updateField("review_count", Number(event.target.value))
            }
            className="w-full rounded-md border border-gray-300 px-3 py-2 outline-none focus:border-gray-500"
          />
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">
            Competitor Count
          </label>
          <input
            type="number"
            min="0"
            step="1"
            value={formData.competitor_count}
            onChange={(event) =>
              updateField("competitor_count", Number(event.target.value))
            }
            className="w-full rounded-md border border-gray-300 px-3 py-2 outline-none focus:border-gray-500"
          />
        </div>
      </div>

      <button
        type="submit"
        disabled={isLoading}
        className="rounded-md bg-black px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isLoading ? "Analyzing..." : "Analyze Product"}
      </button>
    </form>
  );
}
