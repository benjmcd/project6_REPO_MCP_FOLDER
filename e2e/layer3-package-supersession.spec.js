/**
 * W1-S9: Package supersession rendered controls — Playwright spec
 *
 * Proves:
 *   (a) Package supersession history panel renders in blocked state by default
 *       (no replacement authority or commit present).
 *   (b) Record-replacement-set authority button (replacement-package-set-authority-submit)
 *       and commit-supersession button (package-supersession-commit-submit) are disabled
 *       by default (fail-closed until prerequisite authority present).
 *   (c) History projection panel renders in ready state when mocked authority is injected
 *       via page.evaluate, reflecting recorded replacement authority and commit.
 *   (d) Control presence: both submit buttons are present in the DOM inside package-review-band.
 *
 * Route mock strategy: page.route intercepts bootstrap and identity routes so the test
 * server does not need a live DB session. State injection via page.evaluate drives the
 * render functions directly, mirroring the pattern from W1-S7.
 *
 * Safety boundaries: value-reveal-enabled and production-readiness-claimed are always false
 * on the history panel; raw URLs / tokens are never rendered.
 */
import { test, expect } from '@playwright/test';

const IDENTITY_PATH = '/review/layer3/operator/identity';
const BOOTSTRAP_PATH = '**/api/v1/layer3/bootstrap';

// Minimal local identity so the chip renders without blocking.
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

// Minimal bootstrap so the workbench loads without error.
const MINIMAL_BOOTSTRAP = {
    schema_id: 'layer3.workbench_bootstrap.v1',
    session_id: null,
    has_active_session: false,
    authority_matrix: {},
};

// Simulated replacement-package set authority State entry.
const MOCK_REPLACEMENT_AUTHORITY = {
    schema_id: 'layer3.replacement_package_set_authority.v1',
    replacement_package_set_authority_id: 'test-rpsa-id-w1s9',
    replacement_package_set_id: 'test-rps-id-w1s9',
    replacement_package_set_hash: 'aaaa1111bbbb2222cccc3333dddd4444eeee5555ffff6666aaaa1111bbbb2222',
    authority_basis_hash: 'bbbb2222cccc3333dddd4444eeee5555ffff6666aaaa1111bbbb2222cccc3333',
    replacement_package_kinds: ['canonical_internal', 'user_facing', 'review_facing'],
    replacement_payload_refs: ['ref-ci-w1s9', 'ref-uf-w1s9', 'ref-rf-w1s9'],
    replacement_payload_hashes: [
        'cccc3333dddd4444eeee5555ffff6666aaaa1111bbbb2222cccc3333dddd4444',
        'dddd4444eeee5555ffff6666aaaa1111bbbb2222cccc3333dddd4444eeee5555',
        'eeee5555ffff6666aaaa1111bbbb2222cccc3333dddd4444eeee5555ffff6666',
    ],
    status: 'replacement_package_set_authority_recorded',
    next_state: 'package_supersession_commit_ready',
    downstream_unavailable: [],
};

// Simulated package supersession commit State entry.
const MOCK_SUPERSESSION_COMMIT = {
    schema_id: 'layer3.package_supersession_commit.v1',
    package_supersession_commit_id: 'test-psc-id-w1s9',
    package_supersession_commit_mode: 'replacement_package_set_authority_commit',
    commit_basis_hash: 'ffff6666aaaa1111bbbb2222cccc3333dddd4444eeee5555ffff6666aaaa1111',
    downstream_dependency_hash: 'aaaa1111bbbb2222cccc3333dddd4444eeee5555ffff6666aaaa1111bbbb2222',
    replacement_package_set_authority_id: 'test-rpsa-id-w1s9',
    replacement_package_set_id: 'test-rps-id-w1s9',
    replacement_package_set_hash: 'aaaa1111bbbb2222cccc3333dddd4444eeee5555ffff6666aaaa1111bbbb2222',
    status: 'package_supersession_commit_recorded',
    next_state: 'replacement_package_artifact_manifest_ready',
    downstream_unavailable: [],
};

async function mockLocalIdentity(page) {
    await page.route(IDENTITY_PATH, (route) => {
        route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(LOCAL_IDENTITY_RESPONSE),
        });
    });
}

async function mockBootstrap(page) {
    await page.route(BOOTSTRAP_PATH, (route) => {
        route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(MINIMAL_BOOTSTRAP),
        });
    });
}

test.describe('W1-S9 package supersession rendered controls', () => {
    test('(a) history panel renders in blocked state by default (no authority present)', async ({ page }) => {
        await mockLocalIdentity(page);
        await mockBootstrap(page);

        await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });

        const historyPanel = page.locator('#package-supersession-history-panel');
        await expect(historyPanel).toBeVisible();

        // Blocked state: status-pill must include 'blocked'.
        await expect(historyPanel).toContainText('blocked');

        // data-rendered-mode must match the W1-S9 panel identifier.
        await expect(historyPanel).toHaveAttribute(
            'data-rendered-mode',
            'rendered_package_supersession_history_read_only_projection',
        );

        // Safety flags must be set to false.
        await expect(historyPanel).toHaveAttribute('data-value-reveal-enabled', 'false');
        await expect(historyPanel).toHaveAttribute('data-production-readiness-claimed', 'false');
        await expect(historyPanel).toHaveAttribute('data-frontend-durable-authority', 'false');

        // Must not contain raw URLs or tokens.
        const panelText = await historyPanel.textContent();
        expect(panelText).not.toMatch(/https?:\/\//);
    });

    test('(b) record-replacement-set and commit-supersession buttons are disabled by default', async ({ page }) => {
        await mockLocalIdentity(page);
        await mockBootstrap(page);

        await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });

        // Both buttons must be present in the package-review-band.
        const authorityBtn = page.locator('#replacement-package-set-authority-submit');
        const commitBtn = page.locator('#package-supersession-commit-submit');

        await expect(authorityBtn).toBeVisible();
        await expect(commitBtn).toBeVisible();

        // Both must be disabled (fail-closed: no prerequisite authority present).
        await expect(authorityBtn).toBeDisabled();
        await expect(commitBtn).toBeDisabled();
    });

    test('(c) history panel renders ready state when replacement authority is injected', async ({ page }) => {
        await mockLocalIdentity(page);
        await mockBootstrap(page);

        await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });

        // Inject replacement-package set authority into State and re-render.
        await page.evaluate((authority) => {
            window.State = window.State || {};
            State.replacementPackageSetAuthority = authority;
            if (typeof renderAll === 'function') renderAll();
        }, MOCK_REPLACEMENT_AUTHORITY);

        const historyPanel = page.locator('#package-supersession-history-panel');

        // Panel must no longer be blocked.
        await expect(historyPanel).not.toContainText('package_supersession_history_blocked');

        // Authority id must appear in the panel.
        await expect(historyPanel).toContainText('test-rpsa-id-w1s9');

        // Next state should be shown.
        await expect(historyPanel).toContainText('package_supersession_commit_ready');

        // Safety: no raw URLs.
        const panelText = await historyPanel.textContent();
        expect(panelText).not.toMatch(/https?:\/\//);
    });

    test('(c-commit) history panel reflects committed supersession when commit injected', async ({ page }) => {
        await mockLocalIdentity(page);
        await mockBootstrap(page);

        await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });

        // Inject both authority and commit into State.
        await page.evaluate(({ authority, commit }) => {
            window.State = window.State || {};
            State.replacementPackageSetAuthority = authority;
            State.packageSupersessionCommit = commit;
            if (typeof renderAll === 'function') renderAll();
        }, { authority: MOCK_REPLACEMENT_AUTHORITY, commit: MOCK_SUPERSESSION_COMMIT });

        const historyPanel = page.locator('#package-supersession-history-panel');

        // Panel must show commit-recorded state.
        await expect(historyPanel).toContainText('package_supersession_commit_recorded');

        // Commit id must appear.
        await expect(historyPanel).toContainText('test-psc-id-w1s9');

        // Commit basis hash must appear.
        await expect(historyPanel).toContainText('ffff6666aaaa1111');

        // Status pill must show 'ok'.
        await expect(historyPanel.locator('.status-pill.ok')).toBeVisible();

        // No backend history route note must appear.
        await expect(historyPanel).toContainText('none — no GET/history route exists');
    });

    test('(d) control presence: both package supersession submit buttons exist in package-review-band', async ({ page }) => {
        await mockLocalIdentity(page);
        await mockBootstrap(page);

        await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });

        const band = page.locator('#package-review-band');
        await expect(band).toBeVisible();

        // Record Replacement Set button.
        const authorityBtn = band.locator('#replacement-package-set-authority-submit');
        await expect(authorityBtn).toBeVisible();
        await expect(authorityBtn).toBeDisabled();

        // Commit Supersession button.
        const commitBtn = band.locator('#package-supersession-commit-submit');
        await expect(commitBtn).toBeVisible();
        await expect(commitBtn).toBeDisabled();

        // History panel must be present inside the band.
        const historyPanel = band.locator('#package-supersession-history-panel');
        await expect(historyPanel).toBeVisible();
    });
});
