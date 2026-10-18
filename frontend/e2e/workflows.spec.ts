import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

for (const width of [1505, 390]) {
  test(`source copy and full-document navigation at ${width}px`, async ({
    page,
    context,
  }) => {
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await context.grantPermissions(["clipboard-read", "clipboard-write"]);
    await page.setViewportSize({ width, height: width === 390 ? 844 : 1045 });
    await page.goto("/");
    await page
      .getByRole("button", {
        name: "Koliko dana mogu da radim od kuće?",
        exact: true,
      })
      .click();
    await page
      .getByLabel("Otvori izvor hb-03-chunk-0", { exact: true })
      .click();
    await page
      .getByLabel("Kopiraj odlomak hb-03-chunk-0", { exact: true })
      .click();
    await expect(
      page.getByText("Odlomak i njegova referenca su kopirani."),
    ).toBeVisible();
    const copied = await page.evaluate(() => navigator.clipboard.readText());
    expect(copied).toContain("up to 3 days per week");
    expect(copied).toContain("Remote work policy · 2026");
    expect(copied).toContain("[hb-03-chunk-0]");
    await page
      .locator(".source-item.selected")
      .getByRole("button", { name: "Ceo dokument", exact: true })
      .click();
    await expect(page.locator(".document-chunk.is-cited")).toContainText(
      "up to 3 days per week",
    );
    await expect(page.locator(".document-chunk.is-cited")).toBeFocused();
    await expect(
      page.getByRole("button", { name: "Nazad na razgovor", exact: true }),
    ).toBeInViewport();
    const audit = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
      .analyze();
    expect(
      audit.violations.map((v) => ({
        id: v.id,
        targets: v.nodes.map((n) => n.target),
      })),
    ).toEqual([]);
    await page.screenshot({
      path: test.info().outputPath(`source-document-${width}.png`),
    });
    await page
      .getByRole("button", { name: "Nazad na razgovor", exact: true })
      .click();
    await expect(page.locator(".answer-text")).toContainText("3 days per week");
    expect(errors).toEqual([]);
  });
}

test("history search, remove, undo and persistence keep complete answers", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByRole("button", {
      name: "Koliko dana mogu da radim od kuće?",
      exact: true,
    })
    .click();
  await expect(page.locator(".answer-text")).toContainText("3 days per week");
  await page
    .getByRole("button", { name: "Novi razgovor", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Koji je budžet za obuke?", exact: true })
    .click();
  await expect(page.locator(".answer-text")).toContainText("800");
  await expect(page.locator(".history-row")).toHaveCount(2);
  await page.getByLabel("Pretraži razgovore").fill("remotely");
  await expect(page.locator(".history-row")).toHaveCount(1);
  await page
    .getByLabel(
      "Ukloni razgovor: How many days per week can I work remotely?",
      { exact: true },
    )
    .click();
  await expect(page.locator(".history-row")).toHaveCount(0);
  await page.getByRole("button", { name: "Vrati", exact: true }).click();
  await expect(page.locator(".history-row")).toHaveCount(2);
  await expect(page.locator(".answer-text")).toContainText("3 days per week");
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

test("connection failure shows retry instructions and clears stale sources", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByRole("button", {
      name: "Koliko dana mogu da radim od kuće?",
      exact: true,
    })
    .click();
  await expect(page.locator(".source-item")).toHaveCount(2);
  await page.route("**/api/chat", (route) => route.abort("failed"));
  await page
    .getByLabel("Pitanje o priručniku")
    .fill("What is the parental leave policy?");
  await page.getByLabel("Pošalji pitanje", { exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("start-web.command");
  await expect(page.locator(".source-item")).toHaveCount(0);
  await page
    .getByRole("button", { name: "Vrati pitanje u unos", exact: true })
    .click();
  await expect(page.getByLabel("Pitanje o priručniku")).toHaveValue(
    "What is the parental leave policy?",
  );
});
