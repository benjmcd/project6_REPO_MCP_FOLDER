"use client";

import { useMemo, useState } from "react";

import {
  analystInsightSample,
  analystIntegrationSample,
  analystValidationSample,
} from "@/lib/analyst-samples";
import {
  postAnalystInsight,
  postAnalystIntegration,
  postAnalystValidation,
  readApiV1Base,
} from "@/lib/review-api";
import type {
  AnalystInsightRequest,
  AnalystIntegrationRequest,
  AnalystValidationRequest,
} from "@/lib/review-types";
import {
  JsonBlock,
  Panel,
  StatusBanner,
  SurfaceIntro,
  type SurfaceBadge,
} from "@/components/sandbox-primitives";

type StageState = {
  status: "idle" | "running" | "success" | "error";
  output: string;
};

function formatStageError(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  return "Unknown error.";
}

function parseJson<T>(value: string): T {
  return JSON.parse(value) as T;
}

export function AnalystInsightShell() {
  const [integrationInput, setIntegrationInput] = useState(() =>
    JSON.stringify(analystIntegrationSample, null, 2),
  );
  const [validationInput, setValidationInput] = useState(() =>
    JSON.stringify(analystValidationSample, null, 2),
  );
  const [insightInput, setInsightInput] = useState(() =>
    JSON.stringify(analystInsightSample, null, 2),
  );
  const [integrationState, setIntegrationState] = useState<StageState>({
    status: "idle",
    output: 'Click "Run stage 1" to call the integration alias.',
  });
  const [validationState, setValidationState] = useState<StageState>({
    status: "idle",
    output: 'Click "Run stage 2" to call the validation alias.',
  });
  const [insightState, setInsightState] = useState<StageState>({
    status: "idle",
    output: 'Click "Run stage 3" to call the insight alias.',
  });
  const [fullFlowState, setFullFlowState] = useState<StageState>({
    status: "idle",
    output: 'Click "Run full analyst flow" to chain all three aliases.',
  });

  const badges = useMemo<SurfaceBadge[]>(
    () => [
      {
        label: "API root",
        value: readApiV1Base() ?? "Unconfigured",
        tone: readApiV1Base() ? "accent" : "warning",
      },
      { label: "Stage aliases", value: "3", tone: "neutral" },
      { label: "Mode", value: "POST only", tone: "neutral" },
    ],
    [],
  );

  async function runIntegrationStage() {
    let payload: AnalystIntegrationRequest;
    try {
      payload = parseJson<AnalystIntegrationRequest>(integrationInput);
    } catch (error) {
      setIntegrationState({
        status: "error",
        output: `Invalid JSON: ${formatStageError(error)}`,
      });
      return;
    }

    setIntegrationState({ status: "running", output: "Running stage 1..." });
    try {
      const response = await postAnalystIntegration(payload);
      setIntegrationState({
        status: "success",
        output: JSON.stringify(response, null, 2),
      });
    } catch (error) {
      setIntegrationState({
        status: "error",
        output: formatStageError(error),
      });
    }
  }

  async function runValidationStage() {
    let payload: AnalystValidationRequest;
    try {
      payload = parseJson<AnalystValidationRequest>(validationInput);
    } catch (error) {
      setValidationState({
        status: "error",
        output: `Invalid JSON: ${formatStageError(error)}`,
      });
      return;
    }

    setValidationState({ status: "running", output: "Running stage 2..." });
    try {
      const response = await postAnalystValidation(payload);
      setValidationState({
        status: "success",
        output: JSON.stringify(response, null, 2),
      });
    } catch (error) {
      setValidationState({
        status: "error",
        output: formatStageError(error),
      });
    }
  }

  async function runInsightStage() {
    let payload: AnalystInsightRequest;
    try {
      payload = parseJson<AnalystInsightRequest>(insightInput);
    } catch (error) {
      setInsightState({
        status: "error",
        output: `Invalid JSON: ${formatStageError(error)}`,
      });
      return;
    }

    setInsightState({ status: "running", output: "Running stage 3..." });
    try {
      const response = await postAnalystInsight(payload);
      setInsightState({
        status: "success",
        output: JSON.stringify(response, null, 2),
      });
    } catch (error) {
      setInsightState({
        status: "error",
        output: formatStageError(error),
      });
    }
  }

  async function runFullFlow() {
    setFullFlowState({
      status: "running",
      output: "Running stages 1 -> 2 -> 3...",
    });

    try {
      const integrated = await postAnalystIntegration(analystIntegrationSample);

      const flatRows = extractValidationRows(integrated);
      const validated = await postAnalystValidation({
        rows: flatRows.length > 0 ? flatRows : [{ note: "no_cross_refs", region: "USW" }],
        options: {
          required_fields: [],
          numeric_columns: ["tons", "spread_bps"].filter((column) =>
            flatRows.some((row) => column in row),
          ),
          outlier_method: "none",
          normalize_columns: [],
        },
      });

      const insightPayload = buildInsightPayload(integrated, validated);
      const insights = await postAnalystInsight(insightPayload);

      setFullFlowState({
        status: "success",
        output: JSON.stringify(
          {
            stage1_integration: integrated,
            stage2_validation: validated,
            stage3_insight_input: insightPayload,
            stage3_insights: insights,
          },
          null,
          2,
        ),
      });
    } catch (error) {
      setFullFlowState({
        status: "error",
        output: formatStageError(error),
      });
    }
  }

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(14,165,233,0.14),_transparent_26%),linear-gradient(180deg,_#f7fafc_0%,_#eef4f8_100%)] text-slate-950">
      <div className="mx-auto flex w-full max-w-[1600px] flex-col gap-5 px-6 py-6">
        <SurfaceIntro
          title="Analyst Insight"
          detail="This sandbox route ports the live analyst-insight page into the Next-based Onlook lane. It exercises the three aliased POST endpoints directly against the same backend services without touching the shipped static UI."
          badges={badges}
        />

        <div className="grid gap-5 xl:grid-cols-2">
          <StagePanel
            title="Stage 1: Integration"
            endpoint="POST /analyst-insight/integration/cross-reference"
            input={integrationInput}
            status={integrationState.status}
            output={integrationState.output}
            onChange={setIntegrationInput}
            onReset={() =>
              setIntegrationInput(JSON.stringify(analystIntegrationSample, null, 2))
            }
            onRun={() => void runIntegrationStage()}
          />
          <StagePanel
            title="Stage 2: Validation"
            endpoint="POST /analyst-insight/validation/run"
            input={validationInput}
            status={validationState.status}
            output={validationState.output}
            onChange={setValidationInput}
            onReset={() =>
              setValidationInput(JSON.stringify(analystValidationSample, null, 2))
            }
            onRun={() => void runValidationStage()}
          />
        </div>

        <StagePanel
          title="Stage 3: Insight"
          endpoint="POST /analyst-insight/insights/process"
          input={insightInput}
          status={insightState.status}
          output={insightState.output}
          onChange={setInsightInput}
          onReset={() =>
            setInsightInput(JSON.stringify(analystInsightSample, null, 2))
          }
          onRun={() => void runInsightStage()}
        />

        <Panel
          title="Full Flow"
          subtitle="Uses the stage-1 sample, derives validation rows from cross references, then composes the deterministic insight payload from the earlier outputs."
        >
          <div className="flex flex-col gap-4">
            <div className="flex flex-wrap gap-3">
              <button
                type="button"
                onClick={() => void runFullFlow()}
                className="rounded-full bg-slate-950 px-5 py-2 text-sm font-medium text-white transition hover:bg-slate-800"
              >
                Run full analyst flow
              </button>
            </div>
            {fullFlowState.status === "running" ? (
              <StatusBanner message="Running all analyst stages..." tone="info" />
            ) : null}
            {fullFlowState.status === "error" ? (
              <StatusBanner message="Full flow failed. Inspect the output below." tone="error" />
            ) : null}
            {fullFlowState.status === "success" ? (
              <StatusBanner message="Full flow completed successfully." tone="success" />
            ) : null}
            <JsonBlock value={safeJsonParse(fullFlowState.output) ?? fullFlowState.output} />
          </div>
        </Panel>
      </div>
    </main>
  );
}

function StagePanel({
  title,
  endpoint,
  input,
  output,
  status,
  onChange,
  onReset,
  onRun,
}: {
  title: string;
  endpoint: string;
  input: string;
  output: string;
  status: StageState["status"];
  onChange: (value: string) => void;
  onReset: () => void;
  onRun: () => void;
}) {
  const outputJson = safeJsonParse(output);

  return (
    <Panel title={title} subtitle={endpoint}>
      <div className="flex flex-col gap-4">
        <label className="flex flex-col gap-2 text-sm font-medium text-slate-700">
          Request JSON
          <textarea
            value={input}
            onChange={(event) => onChange(event.target.value)}
            spellCheck={false}
            className="min-h-[17rem] rounded-2xl border border-slate-200 bg-slate-50/80 px-4 py-3 font-mono text-xs leading-6 text-slate-900 outline-none transition focus:border-sky-300 focus:bg-white"
          />
        </label>

        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            onClick={onRun}
            className="rounded-full bg-slate-950 px-5 py-2 text-sm font-medium text-white transition hover:bg-slate-800"
          >
            Run {title.toLowerCase()}
          </button>
          <button
            type="button"
            onClick={onReset}
            className="rounded-full border border-slate-200 bg-white px-5 py-2 text-sm font-medium text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
          >
            Reset sample
          </button>
        </div>

        {status === "running" ? (
          <StatusBanner message="Request in flight..." tone="info" />
        ) : null}
        {status === "error" ? (
          <StatusBanner message="Request failed. Inspect the output below." tone="error" />
        ) : null}
        {status === "success" ? (
          <StatusBanner message="Request completed successfully." tone="success" />
        ) : null}

        <div className="flex flex-col gap-2">
          <div className="text-sm font-medium text-slate-700">Response</div>
          <JsonBlock value={outputJson ?? output} />
        </div>
      </div>
    </Panel>
  );
}

function safeJsonParse(value: string): unknown | null {
  try {
    return JSON.parse(value) as unknown;
  } catch {
    return null;
  }
}

function extractValidationRows(
  integrated: Record<string, unknown>,
): Array<Record<string, unknown>> {
  const groups = Array.isArray(integrated.cross_references)
    ? integrated.cross_references
    : [];
  const rows: Array<Record<string, unknown>> = [];

  groups.forEach((group) => {
    if (!isRecord(group)) {
      return;
    }

    const key = isRecord(group.key) ? group.key : {};
    const recordsBySource = isRecord(group.records_by_source)
      ? group.records_by_source
      : {};

    Object.entries(recordsBySource).forEach(([sourceName, records]) => {
      if (!Array.isArray(records)) {
        return;
      }

      records.forEach((record) => {
        if (!isRecord(record)) {
          return;
        }
        rows.push({ ...key, _source: sourceName, ...record });
      });
    });
  });

  return rows;
}

function buildInsightPayload(
  integrated: Record<string, unknown>,
  validated: Record<string, unknown>,
): AnalystInsightRequest {
  const sourceRecordCounts = isRecord(integrated.source_record_counts)
    ? integrated.source_record_counts
    : {};
  const missingFieldIssues = Array.isArray(validated.missing_field_issues)
    ? validated.missing_field_issues
    : [];

  return {
    validation_summary: {
      valid_count:
        typeof validated.row_count === "number" ? validated.row_count : 0,
      invalid_count: missingFieldIssues.length,
      failed_count: 0,
      pass_rate: 0.95,
    },
    integrated: {
      signals_by_category: {
        shipping:
          typeof sourceRecordCounts.shipping === "number"
            ? sourceRecordCounts.shipping
            : 0,
        bonds:
          typeof sourceRecordCounts.bonds === "number"
            ? sourceRecordCounts.bonds
            : 0,
        regulatory:
          typeof sourceRecordCounts.regulatory === "number"
            ? sourceRecordCounts.regulatory
            : 0,
      },
      signal_trajectory: [1.0, 1.1, 1.2, 1.5],
    },
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
