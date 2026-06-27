import { test, expect } from '@playwright/test';

const AUTH_MESSAGE = 'Operator role required for this review surface.';
const AUTH_ACTION = 'request_layer3_operator_role';

async function fulfillAuthEnvelope(route) {
  await route.fulfill({
    status: 403,
    contentType: 'application/json',
    body: JSON.stringify({
      schema_id: 'layer3.auth_error.v1',
      error_code: 'role_access_forbidden',
      message: AUTH_MESSAGE,
      next_allowed_actions: [AUTH_ACTION],
      blocked_fields: ['operator_identity'],
    }),
  });
}

async function expectAuthGuidance(locator) {
  await expect(locator).toContainText(AUTH_MESSAGE);
  await expect(locator).toContainText(`Next action: ${AUTH_ACTION}`);
}

test('NRC APS review surface renders structured auth envelope guidance', async ({ page }) => {
  await page.route('**/api/v1/review/nrc-aps/runs', fulfillAuthEnvelope);

  await page.goto('/review/nrc-aps', { waitUntil: 'domcontentloaded' });

  await expectAuthGuidance(page.locator('#disabled-overlay'));
});

test('Document Trace renders auth guidance for shell and tab-level failures', async ({ page }) => {
  await page.route('**/api/v1/review/nrc-aps/runs', fulfillAuthEnvelope);

  await page.goto('/review/nrc-aps/document-trace', { waitUntil: 'domcontentloaded' });

  await expectAuthGuidance(page.locator('#disabled-overlay'));

  await page.unroute('**/api/v1/review/nrc-aps/runs');
  await page.goto('/review/nrc-aps/document-trace', { waitUntil: 'domcontentloaded' });
  await expect(page.locator('#trace-workspace')).toBeVisible();

  await page.route('**/api/v1/review/nrc-aps/runs/*/documents/*/diagnostics', fulfillAuthEnvelope);
  await page.getByRole('button', { name: /diagnostics/i }).click();

  await expectAuthGuidance(page.locator('#tab-content-area'));
});

test('Workbench Compare and Candidate B Trace render structured auth envelope guidance', async ({ page }) => {
  await page.route('**/api/v1/review/nrc-aps/workbench-compare/sources', fulfillAuthEnvelope);
  await page.goto('/review/nrc-aps/workbench-compare', { waitUntil: 'domcontentloaded' });
  await expectAuthGuidance(page.locator('#disabled-overlay'));

  await page.unroute('**/api/v1/review/nrc-aps/workbench-compare/sources');
  await page.route('**/api/v1/review/nrc-aps/candidate-b-trace/manifest**', fulfillAuthEnvelope);
  await page.goto('/review/nrc-aps/candidate-b-trace?candidate_b_bundle_id=bundle-1&fixture_id=fixture-1', {
    waitUntil: 'domcontentloaded',
  });
  await expectAuthGuidance(page.locator('#disabled-overlay'));
});

test('Analyst Insight renders auth envelope message and next actions without dumping raw JSON', async ({ page }) => {
  await page.route('**/api/v1/analyst-insight/integration/cross-reference', fulfillAuthEnvelope);

  await page.goto('/review/nrc-aps/static/analyst_insight.html', { waitUntil: 'domcontentloaded' });
  await page.locator('#btn-integration').click();

  const output = page.locator('#integration-out');
  await expectAuthGuidance(output);
  await expect(output).not.toContainText('"next_allowed_actions"');
});

test('Analyst Insight full flow derives stage-3 headline metrics from live stage outputs', async ({ page }) => {
  let insightPayload = null;

  await page.route('**/api/v1/analyst-insight/integration/cross-reference', async (route) => {
    await route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({
        cross_references: [
          {
            key: { region: 'USW', date: '2026-01-15' },
            records_by_source: {
              shipping: [{ vessel_id: 'MV1', tons: 1200 }],
              bonds: [{ spread_bps: 45 }],
              regulatory: [{ rule_id: 'R-9' }],
            },
          },
        ],
        source_record_counts: { shipping: 1, bonds: 1, regulatory: 1 },
      }),
    });
  });
  await page.route('**/api/v1/analyst-insight/validation/run', async (route) => {
    await route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({
        row_count: 3,
        valid_count: 2,
        invalid_count: 1,
        failed_count: 1,
        pass_rate: 2 / 3,
        missing_field_issues: [{ field: 'price', row_index: 2 }],
      }),
    });
  });
  await page.route('**/api/v1/analyst-insight/insights/process', async (route) => {
    insightPayload = route.request().postDataJSON();
    await route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({ insight_id: 'insight-derived-1', accepted: true }),
    });
  });

  await page.goto('/review/nrc-aps/static/analyst_insight.html', { waitUntil: 'domcontentloaded' });
  await page.locator('#btn-full-flow').click();
  await expect(page.locator('#full-out')).toContainText('stage3_insight_input');

  expect(insightPayload.validation_summary.valid_count).toBe(2);
  expect(insightPayload.validation_summary.invalid_count).toBe(1);
  expect(insightPayload.validation_summary.failed_count).toBe(1);
  expect(insightPayload.validation_summary.pass_rate).toBeCloseTo(2 / 3, 6);
  expect(insightPayload.integrated.signal_trajectory).toEqual([1, 2, 3]);
});

test('Workbench Compare escapes per-column deep_link href attributes', async ({ page }) => {
  const injectedDeepLink = '/review/nrc-aps/document-trace?target_id=fixture-1" onmouseover="window.__deepLinkInjected=1';

  await page.route('**/api/v1/review/nrc-aps/workbench-compare/**', async (route) => {
    const url = route.request().url();
    if (url.includes('/sources')) {
      await route.fulfill({
        contentType: 'application/json',
        body: JSON.stringify({
          default_baseline_run_id: 'baseline-run',
          default_candidate_a_run_id: 'candidate-a-run',
          default_candidate_b_source_kind: 'bundle',
          default_candidate_b_bundle_id: 'candidate-b-bundle',
          baseline_runs: [{ run_id: 'baseline-run', display_label: 'Baseline' }],
          candidate_a_runs: [{ run_id: 'candidate-a-run', display_label: 'Candidate A' }],
          candidate_b_bundles: [{ bundle_id: 'candidate-b-bundle', display_label: 'Candidate B' }],
          candidate_b_runtime_runs: [],
        }),
      });
      return;
    }
    if (url.includes('/targets/') && url.includes('/manifest')) {
      await route.fulfill({
        contentType: 'application/json',
        body: JSON.stringify({
          source_identity: { fixture_id: 'fixture-1', document_title: 'Fixture' },
          variant_bindings: {},
          summary_badges: [],
          tabs: [{ tab_id: 'summary', label: 'Summary', available: true }],
          warnings: [],
          limitations: [],
          deep_links: {},
        }),
      });
      return;
    }
    if (url.includes('/tabs/summary')) {
      await route.fulfill({
        contentType: 'application/json',
        body: JSON.stringify({
          tab_id: 'summary',
          columns: {
            baseline: {
              label: 'Baseline',
              comparability_class: 'aligned',
              deep_link: injectedDeepLink,
              data: { state: 'ok' },
            },
            candidate_a: { label: 'Candidate A', comparability_class: 'aligned', data: { state: 'ok' } },
            candidate_b: { label: 'Candidate B', comparability_class: 'aligned', data: { state: 'ok' } },
          },
          comparability_legend: { aligned: 'Aligned' },
        }),
      });
      return;
    }
    await route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({
        default_fixture_id: 'fixture-1',
        targets: [{ fixture_id: 'fixture-1', display_label: 'Fixture' }],
      }),
    });
  });

  await page.goto('/review/nrc-aps/workbench-compare', { waitUntil: 'domcontentloaded' });

  const link = page.locator('a.compare-column-link').first();
  await expect(link).toHaveCount(1);
  await expect(link).not.toHaveAttribute('onmouseover', /.+/);
});

test('Candidate B Trace caches a JSON null payload without repeated raw-json fetches', async ({ page }) => {
  let rawJsonFetches = 0;

  await page.route('**/api/v1/review/nrc-aps/candidate-b-trace/manifest**', async (route) => {
    await route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({
        candidate_b_bundle_id: 'bundle-1',
        fixture_id: 'fixture-1',
        default_tab: 'raw_json',
        identity: {
          fixture_id: 'fixture-1',
          bundle_id: 'bundle-1',
          candidate_b_run_id: 'candidate-b-run',
          document_title: 'Fixture',
          source_file_name: 'fixture.pdf',
          document_ref: 'fixture-ref',
        },
        summary: {
          processing_status: 'succeeded',
          decision_recommendation: 'accept',
          annotated_pdf_status: 'missing',
        },
        tabs: [
          { tab_id: 'summary', label: 'Summary', available: true },
          { tab_id: 'raw_json', label: 'Raw JSON', available: true },
        ],
        artifacts: {
          annotated_pdf: null,
          raw_json: '/api/v1/review/nrc-aps/candidate-b-trace/raw-json?fixture_id=fixture-1',
          raw_markdown: null,
        },
        warnings: [],
        limitations: [],
      }),
    });
  });
  await page.route('**/api/v1/review/nrc-aps/candidate-b-trace/raw-json**', async (route) => {
    rawJsonFetches += 1;
    await route.fulfill({
      contentType: 'application/json',
      body: 'null',
    });
  });

  await page.goto('/review/nrc-aps/candidate-b-trace?candidate_b_bundle_id=bundle-1&fixture_id=fixture-1&tab=raw_json', {
    waitUntil: 'domcontentloaded',
  });
  await expect(page.locator('#tab-content-area')).toContainText('null');

  await page.getByRole('button', { name: 'Summary' }).click();
  await page.getByRole('button', { name: 'Raw JSON' }).click();

  expect(rawJsonFetches).toBe(1);
});
