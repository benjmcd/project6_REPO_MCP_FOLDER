import type {
  AnalystInsightRequest,
  AnalystIntegrationRequest,
  AnalystValidationRequest,
} from "@/lib/review-types";

export const analystIntegrationSample: AnalystIntegrationRequest = {
  sources: {
    shipping: [
      { vessel_id: "MV1", region: "USW", date: "2026-01-15", tons: 1200 },
    ],
    bonds: [{ region: "USW", date: "2026-01-15", spread_bps: 45 }],
    regulatory: [{ region: "USW", date: "2026-01-15", rule_id: "R-9" }],
  },
  link_keys: ["region", "date"],
};

export const analystValidationSample: AnalystValidationRequest = {
  rows: [
    { entity: "A", price: 10.0 },
    { entity: "B", price: 11.0 },
    { entity: "C", price: 99.0 },
  ],
  options: {
    required_fields: ["entity", "price"],
    numeric_columns: ["price"],
    outlier_method: "zscore",
    zscore_threshold: 2.0,
    normalize_columns: ["price"],
  },
};

export const analystInsightSample: AnalystInsightRequest = {
  validation_summary: {
    valid_count: 100,
    invalid_count: 4,
    failed_count: 0,
    pass_rate: 0.92,
  },
  integrated: {
    signals_by_category: { shipping: 50, bonds: 45, regulatory: 5 },
    signal_trajectory: [1.0, 1.05, 1.1, 1.4, 1.9],
  },
};
