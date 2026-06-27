(function () {
    const API = "/api/v1";
    // DF8: /market-pipeline/* routes stay API aliases; this page uses analyst-insight aliases for the operator UI.

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
        if (el) {
            el.textContent = msg;
        }
    }

    function formatErrorBody(data) {
        const looksLikeAuthEnvelope = data && typeof data === "object" && (
            data.error_code || data.message || data.next_allowed_actions || data.error
        );
        if (window.NrcApsAuthError && looksLikeAuthEnvelope) {
            return window.NrcApsAuthError.formatText(data, { includeStatus: false });
        }
        if (data && typeof data === "object" && data.detail !== undefined) {
            return typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail, null, 2);
        }
        if (typeof data === "object" && data !== null) {
            return JSON.stringify(data, null, 2);
        }
        return String(data);
    }

    function numberOrFallback(value, fallback) {
        const number = Number(value);
        return Number.isFinite(number) ? number : fallback;
    }

    function buildValidationSummary(validated) {
        const missingIssues = Array.isArray(validated.missing_field_issues) ? validated.missing_field_issues.length : 0;
        const rowCount = numberOrFallback(validated.row_count, 0);
        const invalidCount = numberOrFallback(validated.invalid_count, missingIssues);
        const failedCount = numberOrFallback(validated.failed_count, 0);
        const validCount = numberOrFallback(validated.valid_count, Math.max(rowCount - invalidCount - failedCount, 0));
        const passRate = numberOrFallback(validated.pass_rate, rowCount > 0 ? validCount / rowCount : 0);
        return {
            valid_count: validCount,
            invalid_count: invalidCount,
            failed_count: failedCount,
            pass_rate: passRate,
        };
    }

    function buildSignalTrajectory(sourceCounts) {
        const canonicalOrder = ["shipping", "bonds", "regulatory"];
        const remaining = Object.keys(sourceCounts || {})
            .filter(function (key) { return !canonicalOrder.includes(key); })
            .sort();
        let cumulative = 0;
        return canonicalOrder.concat(remaining)
            .filter(function (key) { return sourceCounts[key] !== undefined; })
            .map(function (key) {
                cumulative += numberOrFallback(sourceCounts[key], 0);
                return cumulative;
            });
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

    async function runIntegration() {
        const raw = $("integration-json").value;
        let body;
        try {
            body = JSON.parse(raw);
        } catch (e) {
            setOut("integration-out", "Invalid JSON: " + e.message, true);
            return;
        }
        setStatus("integration-status", "Running...");
        try {
            const data = await postJson("/analyst-insight/integration/cross-reference", body);
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
        setStatus("validation-status", "Running...");
        try {
            const data = await postJson("/analyst-insight/validation/run", body);
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
        setStatus("insight-status", "Running...");
        try {
            const data = await postJson("/analyst-insight/insights/process", body);
            setOut("insight-out", JSON.stringify(data, null, 2), false);
            setStatus("insight-status", "OK");
        } catch (e) {
            setOut("insight-out", "HTTP " + (e.status || "?") + "\n" + e.message, true);
            setStatus("insight-status", "Error");
        }
    }

    async function runFullFlow() {
        setOut("full-out", "Running stages 1 -> 2 -> 3...", false);
        try {
            const integrated = await postJson(
                "/analyst-insight/integration/cross-reference",
                defaults.integration
            );

            const flatRows = [];
            for (const group of integrated.cross_references || []) {
                const key = group.key || {};
                for (const [sourceName, records] of Object.entries(group.records_by_source || {})) {
                    for (const record of records) {
                        flatRows.push({ ...key, _source: sourceName, ...record });
                    }
                }
            }

            const validated = await postJson("/analyst-insight/validation/run", {
                rows: flatRows.length ? flatRows : [{ note: "no_cross_refs", region: "USW" }],
                options: {
                    required_fields: [],
                    numeric_columns: ["tons", "spread_bps"].filter(function (column) {
                        return flatRows.some(function (row) {
                            return column in row;
                        });
                    }),
                    outlier_method: "none",
                    normalize_columns: [],
                },
            });

            const sourceCounts = integrated.source_record_counts || {};
            const insightPayload = {
                validation_summary: buildValidationSummary(validated),
                integrated: {
                    signals_by_category: {
                        shipping: sourceCounts.shipping || 0,
                        bonds: sourceCounts.bonds || 0,
                        regulatory: sourceCounts.regulatory || 0,
                    },
                    signal_trajectory: buildSignalTrajectory(sourceCounts),
                },
            };

            const insights = await postJson("/analyst-insight/insights/process", insightPayload);
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
        $("btn-full-flow").addEventListener("click", runFullFlow);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
