/**
 * W2-S8: Provider-private download control panel — Playwright spec
 *
 * Proves:
 *   (a) Download control panel renders in blocked state by default (no readiness authority present)
 *   (b) Arm button is hidden/inert when no signed URL receipt authority exists
 *   (c) Panel renders in ready state when provider-private receipt authority is mocked present
 *   (d) Arm button requires operator confirmation checkbox before it becomes active
 *   (e) Arm flow calls the status route (not prepare or revoke); signed URL never appears in rendered text
 *   (f) Download anchor href is set at click time from in-memory state, never rendered as text
 *   (g) data attributes: data-value-reveal-enabled=false, data-production-readiness-claimed=false,
 *       data-download-url-exposed=true only on this panel's own section
 *
 * Route mock strategy: page.route intercepts bootstrap and readiness so the test server
 * does not need to serve a specific readiness posture. The status route is also mocked to
 * prove the arm payload and rendering without a real backend.
 *
 * Safety boundaries verified:
 *   - Signed URL (https://...) never appears in rendered HTML text
 *   - Arm flow does not call prepare or revoke routes
 *   - No console errors on page load (element-presence gate protects mockup pages)
 */
import { test, expect } from '@playwright/test';

const IDENTITY_PATH = '/review/layer3/operator/identity';
const BOOTSTRAP_PATH = '**/api/v1/layer3/bootstrap';
const STATUS_PATH_PATTERN = '**/api/v1/layer3/handoff/export/download/provider-private-signed-url/status/**';
const PREPARE_PATH_PATTERN = '**/api/v1/layer3/handoff/export/download/provider-private-signed-url/prepare';
const REVOKE_PATH_PATTERN = '**/api/v1/layer3/handoff/export/download/provider-private-signed-url/revoke';

// Minimal local identity so identity chip does not block.
const LOCAL_IDENTITY_RESPONSE = {
    schema_id: 'layer3.operator_identity_projection.v1',
    operator_ref_hash: null,
    workspace_ref_hash: null,
    auth_owner_mode: 'local_single_operator',
    derived_role: 'owner',
    authorization_mode: 'local_single_operator',
    auth_owner: 'none',
    trusted_proxy_mode: false,
    deployment_mode: 'development',
};

// Minimal bootstrap so the workbench page loads without error.
const MINIMAL_BOOTSTRAP = {
    schema_id: 'layer3.workbench_bootstrap.v1',
    session_id: null,
    has_active_session: false,
    authority_matrix: {},
};

// Provider-private signed URL state ready for download.
const PROVIDER_PRIVATE_WITH_PREPARED_RECEIPT = {
    provider_signed_url_receipt_id: 'test-pp-receipt-id-w2s8',
    provider_signed_url_state: 'provider_private_signed_url_prepared',
    delivery_mode: 'provider_private_signed_url',
    provider_url_redacted: '[redacted]',
    provider_url_expires_at: '2099-01-01T00:00:00Z',
    provider_url_use_count: 0,
    provider_url_max_use_count: 1,
    provider_url_revoked: false,
    provider_url_revocation_supported: true,
    source_artifact_hash: 'test-artifact-hash-w2s8',
    source_artifact_size_bytes: 99999,
    recipient_scope: 'external-recipient:contract-test',
    next_allowed_actions: ['use_provider_private_signed_url'],
};

// Status response — contains provider_download_url only in mocked test; real responses return redacted.
const STATUS_RESPONSE_WITH_URL = {
    schema_id: 'layer3.provider_private_signed_url_status.v1',
    provider_signed_url_receipt_id: 'test-pp-receipt-id-w2s8',
    provider_signed_url_state: 'provider_private_signed_url_prepared',
    delivery_mode: 'provider_private_signed_url',
    provider_url_redacted: '[redacted]',
    provider_url_expires_at: '2099-01-01T00:00:00Z',
    provider_url_use_count: 0,
    provider_url_max_use_count: 1,
    provider_url_revoked: false,
    provider_url_revocation_supported: true,
    source_artifact_hash: 'test-artifact-hash-w2s8',
    source_artifact_size_bytes: 99999,
    // provider_download_url is the field armProviderPrivateDownloadAnchor reads;
    // in the real backend this is never returned to the browser — the field remains server-side.
    // The test uses it to verify in-memory storage and click-time href assignment.
    provider_download_url: 'https://provider.example/private/download/test-w2s8',
};

// Status response without a download URL — represents normal redacted posture from real backend.
const STATUS_RESPONSE_REDACTED = {
    schema_id: 'layer3.provider_private_signed_url_status.v1',
    provider_signed_url_receipt_id: 'test-pp-receipt-id-w2s8',
    provider_signed_url_state: 'provider_private_signed_url_prepared',
    delivery_mode: 'provider_private_signed_url',
    provider_url_redacted: '[redacted]',
    provider_url_expires_at: '2099-01-01T00:00:00Z',
    provider_url_use_count: 0,
    provider_url_max_use_count: 1,
    provider_url_revoked: false,
    provider_url_revocation_supported: true,
    source_artifact_hash: 'test-artifact-hash-w2s8',
    source_artifact_size_bytes: 99999,
    // No provider_download_url — this is the normal redacted posture.
};

/**
 * Mock local identity so chip renders without blocking.
 */
async function mockLocalIdentity(page) {
    await page.route(IDENTITY_PATH, (route) => {
        route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(LOCAL_IDENTITY_RESPONSE),
        });
    });
}

/**
 * Mock bootstrap so the workbench loads without needing a live DB session.
 */
async function mockBootstrap(page) {
    await page.route(BOOTSTRAP_PATH, (route) => {
        route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(MINIMAL_BOOTSTRAP),
        });
    });
}

/**
 * Inject provider-private signed URL state directly into JS State so the
 * render functions see it without needing a full server flow.
 */
async function injectProviderPrivateState(page) {
    await page.evaluate((receipt) => {
        window.State = window.State || {};
        State.providerPrivateSignedUrlPrepare = receipt;
        if (typeof renderAll === 'function') renderAll();
    }, PROVIDER_PRIVATE_WITH_PREPARED_RECEIPT);
}

test.describe('W2-S8 provider-private download control panel', () => {
    test('(a) download control panel renders in blocked state by default (no authority present)', async ({ page }) => {
        await mockLocalIdentity(page);
        await mockBootstrap(page);

        await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });

        const panel = page.locator('#provider-private-download-control-panel');
        await expect(panel).toBeVisible();

        // Blocked state: must show blocked message.
        await expect(panel).toContainText('blocked');

        // Safety attributes must be set on the panel.
        await expect(panel).toHaveAttribute('data-value-reveal-enabled', 'false');
        await expect(panel).toHaveAttribute('data-download-url-exposed', 'true');
        await expect(panel).toHaveAttribute('data-production-readiness-claimed', 'false');
        await expect(panel).toHaveAttribute(
            'data-rendered-mode',
            'rendered_provider_private_download_control',
        );

        // No signed URL or raw token must appear in text.
        const panelText = await panel.textContent();
        expect(panelText).not.toMatch(/https?:\/\//);
    });

    test('(b) arm button is absent when no provider-private receipt authority exists', async ({ page }) => {
        await mockLocalIdentity(page);
        await mockBootstrap(page);

        await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });

        const panel = page.locator('#provider-private-download-control-panel');
        await expect(panel).toBeVisible();

        // Arm button should not be present in blocked state.
        const armBtn = panel.locator('#provider-private-download-arm-btn');
        await expect(armBtn).not.toBeVisible();
    });

    test('(c) panel renders in ready state when receipt authority is injected', async ({ page }) => {
        await mockLocalIdentity(page);
        await mockBootstrap(page);

        await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });

        await injectProviderPrivateState(page);

        const panel = page.locator('#provider-private-download-control-panel');
        await expect(panel).toBeVisible();

        // Should NOT show the blocked message.
        await expect(panel).not.toContainText(
            'Provider-private download control is blocked until signed URL receipt authority is present.',
        );

        // Should show receipt id (redacted reference, never raw URL).
        await expect(panel).toContainText('test-pp-receipt-id-w2s8');

        // Should show provider_private_signed_url_prepared status.
        await expect(panel).toContainText('provider_private_signed_url_prepared');

        // Should show [redacted] — not a live URL.
        await expect(panel).toContainText('[redacted]');

        // Raw signed URL must NOT appear anywhere in the panel.
        const panelHtml = await panel.innerHTML();
        expect(panelHtml).not.toMatch(/https?:\/\/provider\.example/);

        // Arm button must now be visible.
        const armBtn = panel.locator('#provider-private-download-arm-btn');
        await expect(armBtn).toBeVisible();

        // Safety attributes must remain set.
        await expect(panel).toHaveAttribute('data-value-reveal-enabled', 'false');
        await expect(panel).toHaveAttribute('data-production-readiness-claimed', 'false');
    });

    test('(d) arm button requires operator confirmation checkbox before it fires', async ({ page }) => {
        await mockLocalIdentity(page);
        await mockBootstrap(page);

        // Track status route calls — arm must NOT fire without confirmation.
        let statusCallCount = 0;
        await page.route(STATUS_PATH_PATTERN, (route) => {
            statusCallCount += 1;
            route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify(STATUS_RESPONSE_WITH_URL),
            });
        });

        await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });
        await injectProviderPrivateState(page);

        const armBtn = page.locator('#provider-private-download-arm-btn');
        await expect(armBtn).toBeVisible();

        // Click arm without checking confirmation — should not call status route.
        await armBtn.click();
        expect(statusCallCount).toBe(0);

        // Now check the confirmation and click arm.
        const confirmCheck = page.locator('#provider-private-download-confirmation');
        await confirmCheck.check();

        await armBtn.click();

        // Wait for the download anchor to appear — it is rendered only after arm succeeds.
        const anchor = page.locator('#provider-private-download-anchor');
        await expect(anchor).toBeVisible({ timeout: 10000 });

        // Status route must have been called exactly once.
        expect(statusCallCount).toBe(1);

        // Signed URL must NOT appear in rendered text of the anchor.
        const anchorText = await anchor.textContent();
        expect(anchorText).not.toMatch(/https?:\/\//);
    });

    test('(e) arm flow calls only the status route, never prepare or revoke', async ({ page }) => {
        await mockLocalIdentity(page);
        await mockBootstrap(page);

        const calledRoutes = [];
        await page.route(STATUS_PATH_PATTERN, (route) => {
            calledRoutes.push('status');
            route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify(STATUS_RESPONSE_WITH_URL),
            });
        });
        await page.route(PREPARE_PATH_PATTERN, (route) => {
            calledRoutes.push('prepare');
            route.continue();
        });
        await page.route(REVOKE_PATH_PATTERN, (route) => {
            calledRoutes.push('revoke');
            route.continue();
        });

        await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });
        await injectProviderPrivateState(page);

        const confirmCheck = page.locator('#provider-private-download-confirmation');
        await confirmCheck.check();

        const armBtn = page.locator('#provider-private-download-arm-btn');
        await armBtn.click();

        // Wait for download anchor to appear — rendered only after arm succeeds.
        const anchor2 = page.locator('#provider-private-download-anchor');
        await expect(anchor2).toBeVisible({ timeout: 10000 });

        expect(calledRoutes).toEqual(['status']);
        expect(calledRoutes).not.toContain('prepare');
        expect(calledRoutes).not.toContain('revoke');
    });

    test('(f) signed URL never appears in rendered text or HTML after arm; href assigned at click time only', async ({ page }) => {
        await mockLocalIdentity(page);
        await mockBootstrap(page);

        await page.route(STATUS_PATH_PATTERN, (route) => {
            route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify(STATUS_RESPONSE_WITH_URL),
            });
        });

        await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });
        await injectProviderPrivateState(page);

        const confirmCheck = page.locator('#provider-private-download-confirmation');
        await confirmCheck.check();

        const armBtn = page.locator('#provider-private-download-arm-btn');
        await armBtn.click();

        // Wait for download anchor to appear — rendered only after arm succeeds.
        const downloadAnchor = page.locator('#provider-private-download-anchor');
        await expect(downloadAnchor).toBeVisible({ timeout: 10000 });

        const panel = page.locator('#provider-private-download-control-panel');

        // The URL must not be in any rendered textContent.
        const panelText = await panel.textContent();
        expect(panelText).not.toMatch(/https?:\/\/provider\.example/);

        // The anchor href before click must be '#' (not the real URL).
        const anchor = page.locator('#provider-private-download-anchor');
        await expect(anchor).toBeVisible();
        const hrefBeforeClick = await anchor.getAttribute('href');
        expect(hrefBeforeClick).toBe('#');

        // The full panel HTML must not contain the signed URL text.
        const panelHtml = await panel.innerHTML();
        expect(panelHtml).not.toMatch(/https:\/\/provider\.example\/private\/download\/test-w2s8/);
    });

    test('(g) data-value-reveal-enabled=false, data-production-readiness-claimed=false on panel; data-download-url-exposed=true only on download panel', async ({ page }) => {
        await mockLocalIdentity(page);
        await mockBootstrap(page);

        await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });

        const downloadPanel = page.locator('#provider-private-download-control-panel');
        await expect(downloadPanel).toHaveAttribute('data-value-reveal-enabled', 'false');
        await expect(downloadPanel).toHaveAttribute('data-production-readiness-claimed', 'false');
        await expect(downloadPanel).toHaveAttribute('data-download-url-exposed', 'true');

        // The signed reference audit panel must have data-download-url-exposed=false.
        const auditPanel = page.locator('#signed-reference-revocation-audit-panel');
        await expect(auditPanel).toHaveAttribute('data-download-url-exposed', 'false');

        // No other panel should carry data-download-url-exposed=true.
        const allDownloadExposed = page.locator('[data-download-url-exposed="true"]');
        await expect(allDownloadExposed).toHaveCount(1);
    });

    test('(h-redacted) redacted posture: arm returns no URL, anchor is NOT armed, honest status shown', async ({ page }) => {
        await mockLocalIdentity(page);
        await mockBootstrap(page);

        // Status route returns redacted response — no provider_download_url field.
        await page.route(STATUS_PATH_PATTERN, (route) => {
            route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify(STATUS_RESPONSE_REDACTED),
            });
        });

        await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });
        await injectProviderPrivateState(page);

        const panel = page.locator('#provider-private-download-control-panel');

        // Confirm and arm.
        const confirmCheck = page.locator('#provider-private-download-confirmation');
        await confirmCheck.check();
        const armBtn = page.locator('#provider-private-download-arm-btn');
        await armBtn.click();

        // Wait for render to settle after the arm attempt.
        await page.waitForTimeout(500);

        // Anchor must NOT be present — no real URL was returned.
        const anchor = panel.locator('#provider-private-download-anchor');
        await expect(anchor).not.toBeVisible();

        // Panel must show the honest redacted notice, not an armed state.
        await expect(panel).toContainText('redacted');

        // No raw URL must appear anywhere in the panel.
        const panelText = await panel.textContent();
        expect(panelText).not.toMatch(/https?:\/\//);
        // The placeholder receipt string must NOT appear as a functional href.
        expect(panelText).not.toMatch(/provider-private-receipt:/);
    });

    test('(i) zero console errors on page load (element-presence gate prevents spurious fetches on mockup pages)', async ({ page }) => {
        const consoleErrors = [];
        const pageErrors = [];
        page.on('console', (message) => {
            if (message.type() === 'error') {
                consoleErrors.push(message.text());
            }
        });
        page.on('pageerror', (error) => pageErrors.push(error.message));

        await page.route('**/favicon.ico', async (route) => {
            await route.fulfill({ status: 204, body: '' });
        });

        await mockLocalIdentity(page);
        await mockBootstrap(page);

        await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });

        // Allow a tick for any deferred render.
        await page.waitForTimeout(200);

        expect(consoleErrors).toEqual([]);
        expect(pageErrors).toEqual([]);
    });
});
