import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("accessible answer, documents, evaluation and keyboard dialog", async ({
  page,
}) => {
  async function audit() {
    const result = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
      .analyze();
    expect(
      result.violations.map((v) => ({
        id: v.id,
        nodes: v.nodes.map((n) => n.target),
      })),
    ).toEqual([]);
  }
  await page.goto("/");
  await page.getByLabel("Jezik pitanja").selectOption("en");
  await page
    .getByRole("button", {
      name: "Koliko dana mogu da radim od kuće?",
      exact: true,
    })
    .click();
  await expect(page.locator(".answer-text")).toContainText("3 days per week");
  await audit();
  await page.getByRole("button", { name: "Dokumenti", exact: true }).click();
  await expect(page.locator(".document-row")).toHaveCount(9);
  await audit();
  await page.getByRole("button", { name: "Evaluacija", exact: true }).click();
  await expect(page.locator(".results-table tbody tr")).toHaveCount(12);
  await audit();
  await page.getByRole("button", { name: "Lokalno", exact: true }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await audit();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
});

test("cached grounded answer, original citation, independent refusal, and export", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByLabel("Jezik pitanja").selectOption("en");
  await page
    .getByRole("button", {
      name: "Koliko dana mogu da radim od kuće?",
      exact: true,
    })
    .click();
  await expect(page.locator(".answer-text")).toContainText("3 days per week");
  await page.getByLabel("Otvori izvor hb-03-chunk-0", { exact: true }).click();
  await expect(page.locator(".source-item.selected")).toContainText("2026");
  await expect(page.locator(".source-item.selected")).toContainText(
    "up to 3 days per week",
  );
  await page.getByRole("tab", { name: "Tok odluke", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Pretraga priručnika" }),
  ).toBeVisible();
  await page
    .getByLabel("Pitanje o priručniku")
    .fill("What is the parental leave policy?");
  await page.getByLabel("Pitanje o priručniku").press("Enter");
  await expect(page.locator(".refused-label")).toBeVisible();
  await expect(page.locator(".source-trigger").last()).toHaveText(
    "Pogledaj odluku",
  );
  const downloaded = page.waitForEvent("download");
  await page.getByLabel("Preuzmi razgovor").click();
  expect((await downloaded).suggestedFilename()).toBe("izvor-razgovor.md");
});

test("document versions, saved evaluation failures, and real replay", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByLabel("Jezik pitanja").selectOption("en");
  await page.getByRole("button", { name: "Dokumenti", exact: true }).click();
  await expect(page.locator(".document-row")).toHaveCount(9);
  await page.getByLabel("Verzije dokumenata").selectOption("superseded");
  await expect(page.locator(".document-row")).toHaveCount(1);
  await page.locator(".document-row").click();
  await expect(page.locator(".document-detail")).toContainText(
    "Arhiviran · nije u pretrazi",
  );
  await expect(page.locator(".document-text")).toContainText(
    "up to 2 days per week",
  );
  await page.getByRole("button", { name: "Evaluacija", exact: true }).click();
  await page
    .getByRole("tab", { name: "Dodatni test 2 29/32", exact: true })
    .click();
  await page.getByLabel("Samo neuspešni").check();
  await expect(page.locator(".results-table tbody tr")).toHaveCount(3);
  await page.getByLabel("Detalji U13", { exact: true }).click();
  await expect(page.locator(".failure-explanation")).toContainText(
    "Tražena činjenica",
  );
  await page
    .getByRole("button", { name: "Ponovi iz keša", exact: true })
    .click();
  await expect(
    page.getByText("Ponovljena evaluacija iz keša", { exact: true }),
  ).toBeVisible();
  await expect(page.locator(".results-table tbody tr")).toHaveCount(3);
});

test("offline profile works and restores after browser refresh", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByLabel("Jezik pitanja").selectOption("en");
  await page.getByLabel("Režim pretrage").selectOption("offline");
  await page
    .getByLabel("Pitanje o priručniku")
    .fill("How many days of annual leave do employees get?");
  await page.getByLabel("Pošalji pitanje", { exact: true }).click();
  await expect(page.locator(".answer-text")).toContainText("22 days");
  await expect(page.locator(".inspector-note")).toContainText(
    "bez poziva modelima",
  );
  await page.reload();
  await page.locator(".history button").first().click();
  await expect(page.locator(".answer-text")).toContainText("22 days");
});

for (const width of [1505, 1280, 390]) {
  test(`responsive and accessible workspace at ${width}px`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: width === 390 ? 844 : 1045 });
    await page.goto("/");
    await page.getByLabel("Jezik pitanja").selectOption("en");
    await expect(
      page.getByRole("heading", { name: "Odgovori počinju izvorom." }),
    ).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBeTruthy();
    const audit = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
      .analyze();
    expect(
      audit.violations.map((v) => ({
        id: v.id,
        nodes: v.nodes.map((n) => n.target),
      })),
    ).toEqual([]);
    if (width === 390) {
      await page
        .getByRole("button", {
          name: "Koliko dana mogu da radim od kuće?",
          exact: true,
        })
        .click();
      await page
        .getByLabel("Otvori izvor hb-03-chunk-0", { exact: true })
        .click();
      await expect(page.locator(".inspector-wrapper")).toBeVisible();
      await page.getByLabel("Zatvori izvore", { exact: true }).click();
      await expect(page.getByLabel("Pitanje o priručniku")).toBeVisible();
    }
    await page.screenshot({
      path: test.info().outputPath(`workspace-${width}.png`),
    });
  });
}
