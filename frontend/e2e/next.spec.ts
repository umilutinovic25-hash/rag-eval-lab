import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

for (const width of [1505, 390])
  test(`Serbian Cyrillic question, source translation and original at ${width}px`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: width === 390 ? 844 : 1045 });
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(e.message));
    await page.goto("/");
    await page.getByLabel("Režim pretrage").selectOption("offline");
    await page
      .getByLabel("Pitanje o priručniku")
      .fill("Рад на даљину: колико дана недељно?");
    await page.getByLabel("Pošalji pitanje", { exact: true }).click();
    await expect(page.locator(".answer-text")).toContainText("3 dana");
    await expect(page.locator(".question")).toContainText("Рад на даљину");
    await page
      .getByLabel("Otvori izvor hb-03-chunk-0", { exact: true })
      .click();
    await expect(page.locator(".source-item.selected")).toContainText(
      "3 days per week",
    );
    await expect(page.locator(".translated-source").first()).toContainText(
      "3 dana",
    );
    const a11y = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
      .analyze();
    expect(a11y.violations.map((v) => v.id)).toEqual([]);
    expect(errors).toEqual([]);
    await page.screenshot({
      path: test.info().outputPath(`serbian-${width}.png`),
    });
  });

test("concurrent questions in one conversation survive sync, delete and undo", async ({
  page,
  context,
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
  await expect(
    page.getByText("Istorija je sačuvana u ovom browseru.", { exact: true }),
  ).toBeVisible();
  const other = await context.newPage();
  await other.goto("/");
  await other.getByLabel("Jezik pitanja").selectOption("en");
  await other
    .locator(".history")
    .getByRole("button", {
      name: "How many days per week can I work remotely?",
      exact: true,
    })
    .click();
  await page
    .getByLabel("Pitanje o priručniku")
    .fill("What is the yearly training budget per employee?");
  await other
    .getByLabel("Pitanje o priručniku")
    .fill("How often do passwords need to be changed?");
  await Promise.all([
    page.getByLabel("Pošalji pitanje", { exact: true }).click(),
    other.getByLabel("Pošalji pitanje", { exact: true }).click(),
  ]);
  await expect(page.locator(".answer-text")).toHaveCount(3);
  await expect(other.locator(".answer-text")).toHaveCount(3);
  await expect(page.locator(".turns")).toContainText("800");
  await expect(page.locator(".turns")).toContainText("90 days");
  await expect(
    page.getByText("Istorija je sačuvana u ovom browseru.", { exact: true }),
  ).toBeVisible();
  await page
    .getByLabel(
      "Ukloni razgovor: How many days per week can I work remotely?",
      { exact: true },
    )
    .click();
  await expect(other.locator(".history-row")).toHaveCount(0);
  await expect(
    other.getByRole("heading", {
      name: "Odgovori počinju izvorom.",
      exact: true,
    }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Vrati", exact: true }).click();
  await expect(other.locator(".history-row")).toHaveCount(1);
  await other
    .locator(".history")
    .getByRole("button", {
      name: "How many days per week can I work remotely?",
      exact: true,
    })
    .click();
  await expect(other.locator(".answer-text")).toHaveCount(3);
});

test("synthetic slow job displays progress and sends cancellation", async ({
  page,
}) => {
  let cancelled = false;
  const snapshot = () => ({
    id: "slow",
    status: cancelled ? "cancelled" : "running",
    progress: {
      stage: cancelled ? "cancelled" : "judge",
      message: cancelled
        ? "Obrada je otkazana."
        : "Proveravam relevantnost odlomka 1/5.",
    },
    result: null,
    error: null,
    seconds: 1,
    phases: [],
  });
  await page.route("**/api/jobs", (r) =>
    r.fulfill({ status: 202, json: snapshot() }),
  );
  await page.route("**/api/jobs/slow", (r) => r.fulfill({ json: snapshot() }));
  await page.route("**/api/jobs/slow/cancel", (r) => {
    cancelled = true;
    return r.fulfill({ json: snapshot() });
  });
  await page.goto("/");
  await page
    .getByLabel("Pitanje o priručniku")
    .fill("A deliberately slow test");
  await page.getByLabel("Pošalji pitanje", { exact: true }).click();
  await expect(
    page.getByText("Proveravam relevantnost odlomka 1/5.", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Otkaži obradu", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText("Obrada je otkazana");
  expect(cancelled).toBe(true);
  await expect(page.getByLabel("Pitanje o priručniku")).toBeEnabled();
});

test("a saved server job can be checked after reload without resubmitting", async ({
  page,
  request,
}) => {
  const submitted = await request.post("/api/jobs", {
    data: {
      question: "How many days of annual leave do employees get?",
      profile: "offline",
      language: "en",
    },
  });
  const job = await submitted.json();
  await page.addInitScript(
    (id) =>
      localStorage.setItem(
        "izvor.conversations.v1",
        JSON.stringify([
          {
            id: "resume",
            title: "Resumable job",
            turns: [
              {
                id: "turn",
                question: "How many days of annual leave do employees get?",
                jobId: id,
              },
            ],
          },
        ]),
      ),
    job.id,
  );
  await page.goto("/");
  await page
    .locator(".history")
    .getByRole("button", { name: "Resumable job", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Proveri pozadinski posao", exact: true })
    .click();
  await expect(page.locator(".answer-text")).toContainText("22 days");
});
