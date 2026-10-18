import { test, expect } from "@playwright/test";

test("pending history save warns before refresh and completes after the lock is released", async ({
  page,
}) => {
  await page.goto("/");
  await page.evaluate(async () => {
    let locked!: () => void;
    const ready = new Promise<void>((resolve) => {
      locked = resolve;
    });
    void navigator.locks.request("izvor.history.v1", () => {
      locked();
      return new Promise<void>((resolve) => {
        Object.assign(window, { releaseHistoryForTest: resolve });
      });
    });
    await ready;
  });
  await page
    .getByRole("button", {
      name: "Koliko dana mogu da radim od kuće?",
      exact: true,
    })
    .click();
  await expect(page.locator(".answer-text")).toContainText("3 days per week");
  await expect(
    page.getByText("Čuvam istoriju…", { exact: true }),
  ).toBeVisible();
  const dialog = page.waitForEvent("dialog");
  const reload = page.evaluate(() => location.reload());
  const warning = await dialog;
  expect(warning.type()).toBe("beforeunload");
  await warning.dismiss();
  await reload;
  await page.evaluate(() => {
    (
      window as unknown as { releaseHistoryForTest: () => void }
    ).releaseHistoryForTest();
  });
  await expect(
    page.getByText("Istorija je sačuvana u ovom browseru.", { exact: true }),
  ).toBeVisible();
  await page.reload();
  await page
    .locator(".history")
    .getByRole("button", {
      name: "How many days per week can I work remotely?",
      exact: true,
    })
    .click();
  await expect(page.locator(".answer-text")).toContainText("3 days per week");
});

test("a malformed nested chat response becomes an error without blanking the app", async ({
  page,
}) => {
  await page.route("**/api/chat", async (route) => {
    const response = await route.fetch();
    const data = await response.json();
    await route.fulfill({ json: { ...data, citations: [null] } });
  });
  await page.goto("/");
  await page
    .getByRole("button", {
      name: "Koliko dana mogu da radim od kuće?",
      exact: true,
    })
    .click();
  await expect(page.getByRole("alert")).toContainText("neispravn");
  await expect(page.getByLabel("Pitanje o priručniku")).toBeVisible();
});

test("a refused failed question does not claim that nonexistent citations are wrong", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Evaluacija", exact: true }).click();
  await page
    .getByRole("tab", { name: "Dodatni test 2 29/32", exact: true })
    .click();
  await page.getByLabel("Detalji U07", { exact: true }).click();
  await expect(page.locator(".failure-explanation")).toContainText(
    "Pogrešna odluka",
  );
  await expect(page.locator(".failure-explanation")).not.toContainText(
    "Citati uključuju",
  );
});

test("a malformed extra evaluation run becomes an actionable error", async ({
  page,
}) => {
  await page.route("**/api/evaluations", async (route) => {
    const response = await route.fetch();
    const data = await response.json();
    await route.fulfill({
      json: { ...data, runs: { ...data.runs, unexpected: null } },
    });
  });
  await page.goto("/");
  await page.getByRole("button", { name: "Evaluacija", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("neispravn");
  await expect(
    page.getByRole("heading", { name: "Kvalitet koji može da se proveri." }),
  ).toBeVisible();
});

test("version filter clears the previously selected document", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Dokumenti", exact: true }).click();
  await page
    .locator(".document-row")
    .filter({ hasText: "Remote work policy" })
    .click();
  await expect(page.locator(".document-detail h2")).toHaveText(
    "Remote work policy",
  );
  await page.getByLabel("Verzije dokumenata").selectOption("superseded");
  await expect(page.locator(".document-row")).toHaveCount(1);
  await expect(page.locator(".document-detail h2")).toHaveCount(0);
  await expect(
    page.getByRole("heading", { name: "Otvorite dokument", exact: true }),
  ).toBeVisible();
});

test("a stale tab cannot silently overwrite another tab history", async ({
  page,
  context,
}) => {
  const other = await context.newPage();
  await page.goto("/");
  await other.goto("/");
  await page
    .getByRole("button", {
      name: "Koliko dana mogu da radim od kuće?",
      exact: true,
    })
    .click();
  await expect(page.locator(".answer-text")).toContainText("3 days per week");
  await expect
    .poll(() =>
      page.evaluate(() => localStorage.getItem("izvor.conversations.v1")),
    )
    .toContain("3 days per week");
  await other
    .getByRole("button", { name: "Koji je budžet za obuke?", exact: true })
    .click();
  await expect(other.locator(".answer-text")).toContainText("800");
  await expect(other.getByRole("alert")).toContainText("drugom tabu");
  const stored = await page.evaluate(() =>
    localStorage.getItem("izvor.conversations.v1"),
  );
  expect(stored).toContain("3 days per week");
  expect(stored).not.toContain("yearly training budget");
  const download = other.waitForEvent("download");
  await other.getByLabel("Preuzmi razgovor").click();
  expect((await download).suggestedFilename()).toBe("izvor-razgovor.md");
  await other.screenshot({
    path: test.info().outputPath("history-conflict.png"),
  });
});
