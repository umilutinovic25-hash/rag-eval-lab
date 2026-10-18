import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("local library preview, activation, versions and accessible workbench", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Radionica", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Dokazi pre zaključka." }),
  ).toBeVisible();
  await page.getByLabel("Naslov", { exact: true }).fill("Browser test policy");
  await page
    .getByLabel("Tekst dokumenta", { exact: true })
    .fill("Employees receive 17 test credits per month.");
  await page
    .getByRole("button", { name: "Napravi pregled", exact: true })
    .click();
  await expect(page.locator(".work-preview")).toContainText("neaktivan");
  const row = page
    .locator(".library-row")
    .filter({ hasText: "Browser test policy" });
  await row.locator("summary").click();
  await row
    .getByRole("button", { name: "Aktiviraj dokument", exact: true })
    .click();
  await expect(row).toContainText("aktivan");
  await page
    .getByRole("button", { name: "Uporedi verzije", exact: true })
    .click();
  await expect(
    page.getByText("Poređenje verzija nije odgovor o aktuelnoj politici.", {
      exact: false,
    }),
  ).toBeVisible();
  const audit = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(
    audit.violations.map((v) => ({
      id: v.id,
      nodes: v.nodes.map((n) => n.target),
    })),
  ).toEqual([]);
  // Explicitly deactivate the isolated test input so later scenarios have a clean active corpus.
  await row
    .getByRole("button", { name: "Deaktiviraj dokument", exact: true })
    .click();
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});

test("feedback saves exact local answer and backup requires preview", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByLabel("Režim pretrage").selectOption("offline");
  await page.getByLabel("Jezik pitanja").selectOption("en");
  await page
    .getByLabel("Pitanje o priručniku")
    .fill("How many days of annual leave do employees get?");
  await page.getByLabel("Pošalji pitanje").click();
  await expect(page.locator(".answer-text")).toContainText("22 days");
  await page
    .getByText("Provera tvrdnji i ocena odgovora", { exact: true })
    .click();
  await page.getByLabel("Vrsta ocene").selectOption("incomplete");
  await page
    .getByLabel("Komentar", { exact: true })
    .fill("Browser fixture review");
  await page.getByRole("button", { name: "Sačuvaj lokalnu ocenu" }).click();
  await expect(
    page.getByRole("status").filter({ hasText: "Ocena je sačuvana" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Radionica", exact: true }).click();
  await page
    .getByRole("tab", { name: "Kvalitet i poslovi", exact: true })
    .click();
  await expect(
    page.getByText(
      "incomplete · How many days of annual leave do employees get?",
      { exact: true },
    ),
  ).toBeVisible();
  await page
    .getByRole("tab", { name: "Backup razgovora", exact: true })
    .click();
  const dl = page.waitForEvent("download");
  await page
    .getByRole("button", { name: "Preuzmi JSON backup", exact: true })
    .click();
  const download = await dl;
  const file = await download.path();
  await page.getByLabel("Uvezi backup za pregled").setInputFiles(file!);
  await expect(
    page.getByRole("heading", { name: "Pregled uvoza" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Potvrdi uvoz", exact: true }).click();
  await expect(
    page.getByText("Razgovori su dodati.", { exact: false }),
  ).toBeVisible();
});

test("three tabs converge concurrent changes and never resurrect a deletion", async ({
  context,
}) => {
  const pages = await Promise.all([
    context.newPage(),
    context.newPage(),
    context.newPage(),
  ]);
  for (const p of pages) {
    await p.goto("/");
    await p.getByLabel("Režim pretrage").selectOption("offline");
  }
  await Promise.all(
    pages.map(async (p, i) => {
      await p
        .getByLabel("Pitanje o priručniku")
        .fill(`Multi-tab ${i} annual leave days?`);
      await p.getByLabel("Pošalji pitanje").click();
    }),
  );
  for (const p of pages) await expect(p.locator(".history-row")).toHaveCount(3);
  const target = pages[0]
    .locator(".history-row")
    .filter({ hasText: "Multi-tab 0" });
  await Promise.all([
    target.getByRole("button", { name: /Ukloni razgovor/ }).click(),
    (async () => {
      await pages[1]
        .getByRole("button", { name: "Novi razgovor", exact: true })
        .click();
      await pages[1]
        .getByLabel("Pitanje o priručniku")
        .fill("Concurrent addition: training budget?");
      await pages[1].getByLabel("Pošalji pitanje").click();
    })(),
  ]);
  for (const p of pages) {
    await expect(p.locator(".history-row")).toHaveCount(3);
    await expect(
      p.locator(".history-row").filter({ hasText: "Multi-tab 0" }),
    ).toHaveCount(0);
  }
  for (const p of pages) await p.close();
});

test("offline reconnect and quota failure preserve a reviewable in-memory answer", async ({
  page,
  context,
}) => {
  await page.goto("/");
  await page.getByLabel("Režim pretrage").selectOption("offline");
  await context.setOffline(true);
  await page.getByLabel("Pitanje o priručniku").fill("Annual leave days?");
  await page.getByLabel("Pošalji pitanje").click();
  await expect(page.locator(".error-notice")).toContainText(
    "Veza sa lokalnim serverom",
  );
  await context.setOffline(false);
  await page.evaluate(() => {
    Storage.prototype.setItem = function () {
      throw new DOMException("quota", "QuotaExceededError");
    };
  });
  await page
    .getByLabel("Pitanje o priručniku")
    .fill("How many days of annual leave do employees get?");
  await page.getByLabel("Pošalji pitanje").click();
  await expect(page.locator(".answer-text").last()).toContainText("22 days");
  await expect(
    page.getByText("Browser ne može da sačuva ili uskladi istoriju.", {
      exact: false,
    }),
  ).toBeVisible();
  const dl = page.waitForEvent("download");
  await page.getByLabel("Preuzmi razgovor").click();
  expect((await dl).suggestedFilename()).toBe("izvor-razgovor.md");
});

test("configuration comparison retains source filters and quality panels stay accessible", async ({
  page,
}) => {
  // The 150ms button background transition makes axe sample blended colors.
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  await page.getByRole("button", { name: "Radionica", exact: true }).click();
  await page.getByRole("tab", { name: "Eksperimenti", exact: true }).click();
  await page
    .getByRole("combobox", { name: "Dokument", exact: true })
    .selectOption("hb-08");
  await page
    .getByRole("button", { name: "Uporedi konfiguracije", exact: true })
    .click();
  await expect(page.locator(".comparison-answer")).toHaveCount(2);
  await expect(page.locator(".comparison-answer").last()).toContainText(
    "800 EUR",
  );
  expect(
    await page
      .locator(".sidebar")
      .evaluate((el) => Math.round(el.getBoundingClientRect().top)),
  ).toBe(0);
  for (const tab of [
    "Eksperimenti",
    "Kvalitet i poslovi",
    "Backup razgovora",
  ]) {
    await page.getByRole("tab", { name: tab, exact: true }).click();
    const audit = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
      .analyze();
    expect(audit.violations.map((v) => v.id)).toEqual([]);
  }
});
