(function () {
    const API = "/api/v1";

    const defaults = {
        integration: {
            sources: {
                shipping: [
                    { vessel_id: "MV1", region: "USW", date: "2026-01-15", tons: 1200 },
                ],
                bonds: [{ region: "USW", date: "2026-01-15", spread_bps: 45 }],
                regulatory: [{ region: "USW", date: "2026-01-15", rule_id: "R-9" }],
            },
            link_keys: ["region", "date"],
        },
        validation: {
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
        },
        insight: {
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
        },
    };

    function $(id) {
        return document.getElementById(id);
    }

    function setOut(id, text, isError) {
        const el = $(id);
        el.textContent = text;
        el.classList.toggle("error", !!isError);
    }

    function setStatus(id, msg) {
        const el = $(id);
        if (el) el.textContent = msg;
    }

    function formatErrorBody(data) {
        if (data && typeof data === "object" && data.detail !== undefined) {
            return typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail, null, 2);
        }
        if (typeof data === "object" && data !== null) {
            return JSON.stringify(data, null, 2);
        }
        return String(data);
    }

    async function postJson(path, body) {
        const res = await fetch(API + path, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });
        const text = await res.text();
        let data;
        try {
            data = text ? JSON.parse(text) : null;
        } catch {
            data = text;
        }
        if (!res.ok) {
            const err = new Error(formatErrorBody(data));
            err.status = res.status;
            err.payload = data;
            throw err;
        }
        return data;
    }

    const STORAGE_BRIDGE_404_HINT =
        "\n\nIf you expected this run to exist: the API process must use the same Tier1 DATABASE_URL " +
        "as the database where that run was ingested (backend/.env). For SQLite with project6.ps1, " +
        "use -Tier1DatabaseBackend sqlite so .env is honored, then restart the server.";

    async function runIntegration() {
        const raw = $("integration-json").value;
        let body;
        try {
            body = JSON.parse(raw);
        } catch (e) {
            setOut("integration-out", "Invalid JSON: " + e.message, true);
            return;
        }
        setStatus("integration-status", "Running…");
        try {
            const data = await postJson("/market-pipeline/integration/cross-reference", body);
            setOut("integration-out", JSON.stringify(data, null, 2), false);
            setStatus("integration-status", "OK");
        } catch (e) {
            setOut("integration-out", "HTTP " + (e.status || "?") + "\n" + e.message, true);
            setStatus("integration-status", "Error");
        }
    }

    async function runValidation() {
        const raw = $("validation-json").value;
        let body;
        try {
            body = JSON.parse(raw);
        } catch (e) {
            setOut("validation-out", "Invalid JSON: " + e.message, true);
            return;
        }
        setStatus("validation-status", "Running…");
        try {
            const data = await postJson("/market-pipeline/validation/run", body);
            setOut("validation-out", JSON.stringify(data, null, 2), false);
            setStatus("validation-status", "OK");
        } catch (e) {
            setOut("validation-out", "HTTP " + (e.status || "?") + "\n" + e.message, true);
            setStatus("validation-status", "Error");
        }
    }

    async function runInsight() {
        const raw = $("insight-json").value;
        let body;
        try {
            body = JSON.parse(raw);
        } catch (e) {
            setOut("insight-out", "Invalid JSON: " + e.message, true);
            return;
        }
        setStatus("insight-status", "Running…");
        try {
            const data = await postJson("/market-pipeline/insights/process", body);
            setOut("insight-out", JSON.stringify(data, null, 2), false);
            setStatus("insight-status", "OK");
        } catch (e) {
            setOut("insight-out", "HTTP " + (e.status || "?") + "\n" + e.message, true);
            setStatus("insight-status", "Error");
        }
    }

    async function runFullPipeline() {
        setOut("full-out", "Running stages 1 → 2 → 3…", false);
        try {
            const integrated = await postJson(
                "/market-pipeline/integration/cross-reference",
                defaults.integration
            );
            const flatRows = [];
            for (const group of integrated.cross_references || []) {
                const key = group.key || {};
                for (const [src, records] of Object.entries(group.records_by_source || {})) {
                    for (const r of records) {
                        flatRows.push({ ...key, _source: src, ...r });
                    }
                }
            }
            const validated = await postJson("/market-pipeline/validation/run", {
                rows: flatRows.length ? flatRows : [{ note: "no_cross_refs", region: "USW" }],
                options: {
                    required_fields: [],
                    numeric_columns: ["tons", "spread_bps"].filter((c) =>
                        flatRows.some((row) => c in row)
                    ),
                    outlier_method: "none",
                    normalize_columns: [],
                },
            });
            const insightPayload = {
                validation_summary: {
                    valid_count: validated.row_count || 0,
                    invalid_count: (validated.missing_field_issues || []).length,
                    failed_count: 0,
                    pass_rate: 0.95,
                },
                integrated: {
                    signals_by_category: {
                        shipping: (integrated.source_record_counts || {}).shipping || 0,
                        bonds: (integrated.source_record_counts || {}).bonds || 0,
                        regulatory: (integrated.source_record_counts || {}).regulatory || 0,
                    },
                    signal_trajectory: [1.0, 1.1, 1.2, 1.5],
                },
            };
            const insights = await postJson("/market-pipeline/insights/process", insightPayload);
            setOut(
                "full-out",
                JSON.stringify(
                    {
                        stage1_integration: integrated,
                        stage2_validation: validated,
                        stage3_insight_input: insightPayload,
                        stage3_insights: insights,
                    },
                    null,
                    2
                ),
                false
            );
        } catch (e) {
            setOut("full-out", "Pipeline error:\n" + e.message, true);
        }
    }

    function init() {
        $("integration-json").value = JSON.stringify(defaults.integration, null, 2);
        $("validation-json").value = JSON.stringify(defaults.validation, null, 2);
        $("insight-json").value = JSON.stringify(defaults.insight, null, 2);

        $("btn-integration").addEventListener("click", runIntegration);
        $("btn-validation").addEventListener("click", runValidation);
        $("btn-insight").addEventListener("click", runInsight);
        $("btn-reset-integration").addEventListener("click", function () {
            $("integration-json").value = JSON.stringify(defaults.integration, null, 2);
        });
        $("btn-reset-validation").addEventListener("click", function () {
            $("validation-json").value = JSON.stringify(defaults.validation, null, 2);
        });
        $("btn-reset-insight").addEventListener("click", function () {
            $("insight-json").value = JSON.stringify(defaults.insight, null, 2);
        });
        $("btn-full-pipeline").addEventListener("click", runFullPipeline);
        $("btn-doc-storage").addEventListener("click", runDocumentStorageBridge);
    }

    async function runDocumentStorageBridge() {
        const runId = ($("ds-run-id").value || "").trim();
        if (!runId) {
            setOut("ds-out", "Enter a connector_run_id.", true);
            setStatus("ds-status", "");
            return;
        }
        const material = $("ds-material").value;
        setStatus("ds-status", "Running…");
        setOut("ds-out", "Calling /market-pipeline/from-document-storage/…", false);
        try {
            const path =
                "/market-pipeline/from-document-storage/" + encodeURIComponent(runId);
            const data = await postJson(path, {
                material_source: material,
                limit: 80,
                offset: 0,
            });
            setOut("ds-out", JSON.stringify(data, null, 2), false);
            setStatus("ds-status", "OK");
        } catch (e) {
            let msg = "HTTP " + (e.status || "?") + "\n" + e.message;
            if (e.status === 404) {
                msg += STORAGE_BRIDGE_404_HINT;
            }
            setOut("ds-out", msg, true);
            setStatus("ds-status", "Error");
        }
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
