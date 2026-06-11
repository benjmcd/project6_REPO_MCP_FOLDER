/**
 * W1-S6: Operator session UI — Playwright spec
 *
 * Proves:
 *   (a) Identity chip renders under the local (auth_owner=none) profile
 *   (b) Dev-mode header injection control exists under none-mode
 *   (c) Blocked-state rendering when identity fetch is forced to fail
 *
 * Route mock strategy: page.route intercepts /review/layer3/operator/identity
 * so the test server does not need to serve that route in a specific posture.
 */
import { test, expect } from '@playwright/test';

const IDENTITY_PATH = '/api/v1/layer3/operator/identity';

// Stable local-operator identity projection matching the route contract.
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

// 409 canonical error envelope (untrusted proxy posture).
const PROXY_ERROR_RESPONSE = {
    error_code: 'sec_xbrl_in_app_auth_policy_untrusted_proxy_identity',
    message: 'Proxy identity authority is not trusted.',
    next_allowed_actions: ['configure_trusted_proxy_mode'],
};

// 401 canonical error envelope (missing identity).
const MISSING_IDENTITY_RESPONSE = {
    error_code: 'sec_xbrl_in_app_auth_policy_missing_identity_authority',
    message: 'Identity authority header is missing.',
    next_allowed_actions: ['provide_x_forwarded_user_header'],
};

test.describe('W1-S6 operator identity UI', () => {
    test('(a) identity chip renders in local profile (auth_owner=none)', async ({ page }) => {
        // Intercept identity route with local-operator projection.
        await page.route(IDENTITY_PATH, (route) => {
            route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify(LOCAL_IDENTITY_RESPONSE),
            });
        });

        await page.goto('/review/layer3');

        const chip = page.locator('#operator-identity-chip');
        await expect(chip).toBeVisible();

        // Chip must reflect local profile: data-auth-state=local, text contains role.
        await expect(chip).toHaveAttribute('data-auth-state', 'local');
        await expect(chip).toContainText('local');
        await expect(chip).toContainText('owner');
    });

    test('(b) dev-mode header injection control is visible under auth_owner=none', async ({ page }) => {
        await page.route(IDENTITY_PATH, (route) => {
            route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify(LOCAL_IDENTITY_RESPONSE),
            });
        });

        await page.goto('/review/layer3');

        // Wait for identity chip to reflect local state (confirms identity loaded).
        const chip = page.locator('#operator-identity-chip');
        await expect(chip).toHaveAttribute('data-auth-state', 'local');

        // Dev header injection container must be present and not have hidden attribute.
        const devContainer = page.locator('#dev-header-injection');
        await expect(devContainer).not.toHaveAttribute('hidden', '');

        // Open the <details> so that interior elements become visible.
        await devContainer.locator('summary').click();

        // Both input fields must be present and visible after opening.
        await expect(page.locator('#dev-x-forwarded-user')).toBeVisible();
        await expect(page.locator('#dev-x-forwarded-groups')).toBeVisible();

        // Apply button must be present.
        await expect(page.locator('#dev-header-inject-apply')).toBeVisible();
    });

    test('(c) chip and banner render in blocked state when identity fetch fails (409)', async ({ page }) => {
        await page.route(IDENTITY_PATH, (route) => {
            route.fulfill({
                status: 409,
                contentType: 'application/json',
                body: JSON.stringify(PROXY_ERROR_RESPONSE),
            });
        });

        await page.goto('/review/layer3');

        const chip = page.locator('#operator-identity-chip');
        // Chip must be in blocked state.
        await expect(chip).toHaveAttribute('data-auth-state', 'blocked');
        await expect(chip).toContainText('Auth blocked');
        await expect(chip).toContainText('409');

        // Auth banner must appear.
        const banner = page.locator('#operator-auth-banner');
        await expect(banner).not.toHaveAttribute('hidden');
        await expect(banner).toContainText('sec_xbrl_in_app_auth_policy_untrusted_proxy_identity');
        await expect(banner).toContainText('409');

        // Dev header injection must be hidden (not auth_owner=none).
        const devContainer = page.locator('#dev-header-injection');
        await expect(devContainer).toHaveAttribute('hidden', '');
    });

    test('(c-variant) blocked state on 401 missing identity', async ({ page }) => {
        await page.route(IDENTITY_PATH, (route) => {
            route.fulfill({
                status: 401,
                contentType: 'application/json',
                body: JSON.stringify(MISSING_IDENTITY_RESPONSE),
            });
        });

        await page.goto('/review/layer3');

        const chip = page.locator('#operator-identity-chip');
        await expect(chip).toHaveAttribute('data-auth-state', 'blocked');
        await expect(chip).toContainText('Auth blocked');

        const banner = page.locator('#operator-auth-banner');
        await expect(banner).not.toHaveAttribute('hidden');
        await expect(banner).toContainText('sec_xbrl_in_app_auth_policy_missing_identity_authority');
    });
});
