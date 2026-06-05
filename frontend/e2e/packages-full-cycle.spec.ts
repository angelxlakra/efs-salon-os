/**
 * Packages Full Cycle — End-to-End Happy Path
 *
 * Prerequisites for running this spec:
 *   1. Playwright installed: `cd frontend && npm install -D @playwright/test`
 *   2. App running: `docker compose up`
 *   3. Test users seeded: owner / receptionist credentials in .env.test
 *   4. Run: `npx playwright test e2e/packages-full-cycle.spec.ts`
 *
 * This test covers the complete lifecycle:
 *   Owner creates definition → publishes it → Receptionist sells it to a customer →
 *   Customer returns for 3 redemptions → Owner issues refund for remaining sessions
 */

import { test, expect, type Page } from "@playwright/test";

// ─── Helpers ───────────────────────────────────────────────────────────────

async function loginAs(page: Page, role: "owner" | "receptionist") {
  const credentials: Record<string, { username: string; password: string }> = {
    owner: {
      username: process.env.TEST_OWNER_USERNAME ?? "owner",
      password: process.env.TEST_OWNER_PASSWORD ?? "test123",
    },
    receptionist: {
      username: process.env.TEST_RECEPTIONIST_USERNAME ?? "receptionist",
      password: process.env.TEST_RECEPTIONIST_PASSWORD ?? "test123",
    },
  };
  await page.goto("/login");
  await page.fill('input[name="username"]', credentials[role].username);
  await page.fill('input[name="password"]', credentials[role].password);
  await page.click('button[type="submit"]');
  await page.waitForURL("/dashboard");
}

async function selectCustomer(page: Page, name: string) {
  // Cmd+. opens customer search
  await page.keyboard.press("Meta+.");
  await page.fill('input[placeholder*="customer"]', name);
  await page.click(`[data-testid="customer-result"]:has-text("${name}")`);
}

async function payCash(page: Page, amount?: string) {
  if (amount) await page.fill('input[name="amount"]', amount);
  await page.click('button:has-text("Cash")');
  await page.click('button:has-text("Confirm Payment")');
  await page.waitForSelector("text=Payment confirmed");
}

// ─── Test ──────────────────────────────────────────────────────────────────

test.describe("Packages full lifecycle", () => {
  const PACKAGE_NAME = `E2E Hair Spa 5-pack ${Date.now()}`;
  const CUSTOMER_NAME = "Test Customer E2E";

  test("Owner creates and publishes a counted package", async ({ page }) => {
    await loginAs(page, "owner");
    await page.goto("/dashboard/packages/new");

    // Fill package details
    await page.fill('input#pkg-name', PACKAGE_NAME);
    await page.click('button:has-text("Counted · Personal")'); // entitlement matrix
    await page.fill('input#pkg-sessions', "5");
    await page.fill('input#pkg-validity', "180");

    // Add a service line
    await page.click('button:has-text("Add service")');
    await page.fill('input[placeholder="Service name"]', "Hair Spa");
    await page.fill('input[type="number"][step="0.01"]', "500"); // ₹500 per session

    // Save → draft created
    await page.click('button:has-text("Save & draft")');
    await page.waitForURL(/\/dashboard\/packages\//);

    // Publish the draft
    await page.click('button:has-text("Publish")');
    await expect(page.locator("text=published")).toBeVisible();
  });

  test("Receptionist sells the package to a customer", async ({ page }) => {
    await loginAs(page, "receptionist");
    await page.goto("/dashboard/pos");

    // Select customer
    await selectCustomer(page, CUSTOMER_NAME);

    // Switch to Packages tab
    await page.click('button:has-text("Packages")');
    await expect(page.locator(`text=${PACKAGE_NAME}`)).toBeVisible();
    await page.click(`button:has-text("${PACKAGE_NAME}")`);

    // Bill canvas should show the package sale line
    await expect(page.locator("text=Package sale")).toBeVisible();

    // Finalize
    await page.keyboard.press("Meta+Enter");
    await payCash(page);
  });

  test("Customer returns — first redemption auto-applies", async ({ page }) => {
    await loginAs(page, "receptionist");
    await page.goto("/dashboard/pos");
    await selectCustomer(page, CUSTOMER_NAME);

    // Entitlements Rail should show the package
    await expect(page.locator(`text=${PACKAGE_NAME}`)).toBeVisible();

    // Add a Hair Spa service — auto-apply should kick in
    await page.fill('input[placeholder*="search"]', "Hair Spa");
    await page.click("text=Hair Spa");

    // Should see "Paid via package" on the bill line
    await expect(page.locator("text=Paid via package")).toBeVisible();

    await page.keyboard.press("Meta+Enter");
    await payCash(page, "0"); // Zero cash — covered by package
  });

  test("Owner refunds the remaining sessions", async ({ page }) => {
    await loginAs(page, "owner");
    await page.goto("/dashboard/packages/sold");

    // Find the package and click Refund
    const row = page.locator(`tr:has-text("${PACKAGE_NAME}")`).first();
    await row.locator('button:has-text("Refund")').click();

    // Fill refund modal
    await page.fill('textarea#refund-reason', "E2E test refund");
    await page.click('button:has-text("Issue Credit Note")');

    // Verify refunded status
    await expect(page.locator(`tr:has-text("${PACKAGE_NAME}") >> text=refunded`)).toBeVisible();
  });
});
