# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: expansion.spec.ts >> configuration comparison retains source filters and quality panels stay accessible
- Location: e2e/expansion.spec.ts:186:1

# Error details

```
Error: expect(locator).toHaveCount(expected) failed

Locator:  locator('.comparison-answer')
Expected: 2
Received: 0
Timeout:  5000ms

Call log:
  - Expect "toHaveCount" locator('.comparison-answer') with timeout 5000ms
  - waiting for locator('.comparison-answer')
    14 × locator resolved to 0 elements
       - unexpected value "0"

```

# Page snapshot

```yaml
- generic [ref=e3]:
  - complementary [ref=e4]:
    - generic [ref=e5]: izvor.
    - paragraph [ref=e6]: RAG radni prostor
    - navigation "Glavna navigacija" [ref=e7]:
      - button "Razgovor" [ref=e8] [cursor=pointer]
      - button "Dokumenti" [ref=e11] [cursor=pointer]
      - button "Evaluacija" [ref=e15] [cursor=pointer]
      - button "Radionica" [ref=e17] [cursor=pointer]
    - button "Novi razgovor" [ref=e22] [cursor=pointer]
    - button "Lokalni sistem Week 07" [ref=e24] [cursor=pointer]:
      - generic [ref=e27]: Lokalni sistem
      - generic [ref=e29]: Week 07
  - main [ref=e31]:
    - generic [ref=e32]:
      - generic [ref=e33]:
        - generic [ref=e34]: Radni prostor
        - generic [ref=e35]: /
        - strong [ref=e36]: Radionica
      - button "Lokalno" [ref=e38] [cursor=pointer]
    - generic [ref=e40]:
      - generic [ref=e41]:
        - paragraph [ref=e42]: LOKALNA RADIONICA
        - heading "Dokazi pre zaključka." [level=1] [ref=e43]
        - paragraph [ref=e44]: Biblioteka, poređenje konfiguracija i pregled kvaliteta na jednom mestu. Originalni zadatak ostaje sačuvan.
      - tablist "Radionica" [ref=e45]:
        - tab "Biblioteka" [ref=e46] [cursor=pointer]
        - tab "Eksperimenti" [selected] [ref=e47] [cursor=pointer]
        - tab "Kvalitet i poslovi" [ref=e48] [cursor=pointer]
        - tab "Backup razgovora" [ref=e49] [cursor=pointer]
      - tabpanel [ref=e50]:
        - article [ref=e51]:
          - heading "Isto pitanje. Dve konfiguracije." [level=2] [ref=e52]
          - paragraph [ref=e53]: Baseline čuva prethodno ponašanje. Aktuelni profil uključuje nova pravila dokaza. Provereni profil vezuje keš za digest modela i može zahtevati nove lokalne pozive. Engleski upit koristi originalne izvore.
          - generic [ref=e54]:
            - text: Pitanje za poređenje
            - textbox "Pitanje za poređenje" [ref=e55]: Is the training budget per team or per person?
          - generic [ref=e56]:
            - generic [ref=e57]:
              - text: Konfiguracija 1
              - combobox "Konfiguracija 1" [ref=e58]:
                - option "Baseline" [selected]
                - option "Aktuelni"
                - option "Bez modela"
                - option "Digest proveren"
            - generic [ref=e59]:
              - text: Konfiguracija 2
              - combobox "Konfiguracija 2" [ref=e60]:
                - option "Baseline"
                - option "Aktuelni" [selected]
                - option "Bez modela"
                - option "Digest proveren"
          - generic [ref=e61]:
            - generic [ref=e62]:
              - text: Tema
              - combobox "Tema" [ref=e63]:
                - option "Sve teme" [selected]
                - option "IT and equipment"
                - option "Working arrangements"
                - option "Finance"
                - option "Security"
                - option "People"
                - option "Learning"
                - option "Facilities"
                - option "Sandbox"
            - generic [ref=e64]:
              - text: Dokument
              - combobox "Dokument" [ref=e65]:
                - option "Svi dokumenti"
                - option "Equipment replacement · hb-01"
                - option "Remote work policy · hb-02"
                - option "Remote work policy · hb-03"
                - option "Travel expenses · hb-04"
                - option "Passwords and access · hb-05"
                - option "Onboarding · hb-06"
                - option "Annual leave · hb-07"
                - option "Training budget · hb-08" [selected]
                - option "Office access and parking · hb-09"
                - option "IT support · hb-10"
                - option "Browser test policy · local-42361bd4bc474d0cb4476509363c98c0"
            - generic [ref=e66]:
              - text: Važi na datum
              - textbox "Važi na datum" [ref=e67]
            - generic [ref=e68]:
              - checkbox "Uključi aktivne lokalne dokumente" [ref=e69]
              - text: Uključi aktivne lokalne dokumente
          - button "Uporedi konfiguracije" [disabled] [ref=e70]
          - status [ref=e71]: Proveravam relevantnost odlomka 1/2.
          - button "Otkaži poređenje" [ref=e72] [cursor=pointer]
```

# Test source

```ts
  100 |     page.getByRole("heading", { name: "Pregled uvoza" }),
  101 |   ).toBeVisible();
  102 |   await page.getByRole("button", { name: "Potvrdi uvoz", exact: true }).click();
  103 |   await expect(
  104 |     page.getByText("Razgovori su dodati.", { exact: false }),
  105 |   ).toBeVisible();
  106 | });
  107 | 
  108 | test("three tabs converge concurrent changes and never resurrect a deletion", async ({
  109 |   context,
  110 | }) => {
  111 |   const pages = await Promise.all([
  112 |     context.newPage(),
  113 |     context.newPage(),
  114 |     context.newPage(),
  115 |   ]);
  116 |   for (const p of pages) {
  117 |     await p.goto("/");
  118 |     await p.getByLabel("Režim pretrage").selectOption("offline");
  119 |   }
  120 |   await Promise.all(
  121 |     pages.map(async (p, i) => {
  122 |       await p
  123 |         .getByLabel("Pitanje o priručniku")
  124 |         .fill(`Multi-tab ${i} annual leave days?`);
  125 |       await p.getByLabel("Pošalji pitanje").click();
  126 |     }),
  127 |   );
  128 |   for (const p of pages) await expect(p.locator(".history-row")).toHaveCount(3);
  129 |   const target = pages[0]
  130 |     .locator(".history-row")
  131 |     .filter({ hasText: "Multi-tab 0" });
  132 |   await Promise.all([
  133 |     target.getByRole("button", { name: /Ukloni razgovor/ }).click(),
  134 |     (async () => {
  135 |       await pages[1]
  136 |         .getByRole("button", { name: "Novi razgovor", exact: true })
  137 |         .click();
  138 |       await pages[1]
  139 |         .getByLabel("Pitanje o priručniku")
  140 |         .fill("Concurrent addition: training budget?");
  141 |       await pages[1].getByLabel("Pošalji pitanje").click();
  142 |     })(),
  143 |   ]);
  144 |   for (const p of pages) {
  145 |     await expect(p.locator(".history-row")).toHaveCount(3);
  146 |     await expect(
  147 |       p.locator(".history-row").filter({ hasText: "Multi-tab 0" }),
  148 |     ).toHaveCount(0);
  149 |   }
  150 |   for (const p of pages) await p.close();
  151 | });
  152 | 
  153 | test("offline reconnect and quota failure preserve a reviewable in-memory answer", async ({
  154 |   page,
  155 |   context,
  156 | }) => {
  157 |   await page.goto("/");
  158 |   await page.getByLabel("Režim pretrage").selectOption("offline");
  159 |   await context.setOffline(true);
  160 |   await page.getByLabel("Pitanje o priručniku").fill("Annual leave days?");
  161 |   await page.getByLabel("Pošalji pitanje").click();
  162 |   await expect(page.locator(".error-notice")).toContainText(
  163 |     "Veza sa lokalnim serverom",
  164 |   );
  165 |   await context.setOffline(false);
  166 |   await page.evaluate(() => {
  167 |     Storage.prototype.setItem = function () {
  168 |       throw new DOMException("quota", "QuotaExceededError");
  169 |     };
  170 |   });
  171 |   await page
  172 |     .getByLabel("Pitanje o priručniku")
  173 |     .fill("How many days of annual leave do employees get?");
  174 |   await page.getByLabel("Pošalji pitanje").click();
  175 |   await expect(page.locator(".answer-text").last()).toContainText("22 days");
  176 |   await expect(
  177 |     page.getByText("Browser ne može da sačuva ili uskladi istoriju.", {
  178 |       exact: false,
  179 |     }),
  180 |   ).toBeVisible();
  181 |   const dl = page.waitForEvent("download");
  182 |   await page.getByLabel("Preuzmi razgovor").click();
  183 |   expect((await dl).suggestedFilename()).toBe("izvor-razgovor.md");
  184 | });
  185 | 
  186 | test("configuration comparison retains source filters and quality panels stay accessible", async ({
  187 |   page,
  188 | }) => {
  189 |   // The 150ms button background transition makes axe sample blended colors.
  190 |   await page.emulateMedia({ reducedMotion: "reduce" });
  191 |   await page.goto("/");
  192 |   await page.getByRole("button", { name: "Radionica", exact: true }).click();
  193 |   await page.getByRole("tab", { name: "Eksperimenti", exact: true }).click();
  194 |   await page
  195 |     .getByRole("combobox", { name: "Dokument", exact: true })
  196 |     .selectOption("hb-08");
  197 |   await page
  198 |     .getByRole("button", { name: "Uporedi konfiguracije", exact: true })
  199 |     .click();
> 200 |   await expect(page.locator(".comparison-answer")).toHaveCount(2);
      |                                                    ^ Error: expect(locator).toHaveCount(expected) failed
  201 |   await expect(page.locator(".comparison-answer").last()).toContainText(
  202 |     "800 EUR",
  203 |   );
  204 |   expect(
  205 |     await page
  206 |       .locator(".sidebar")
  207 |       .evaluate((el) => Math.round(el.getBoundingClientRect().top)),
  208 |   ).toBe(0);
  209 |   for (const tab of [
  210 |     "Eksperimenti",
  211 |     "Kvalitet i poslovi",
  212 |     "Backup razgovora",
  213 |   ]) {
  214 |     await page.getByRole("tab", { name: tab, exact: true }).click();
  215 |     const audit = await new AxeBuilder({ page })
  216 |       .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
  217 |       .analyze();
  218 |     expect(audit.violations.map((v) => v.id)).toEqual([]);
  219 |   }
  220 | });
  221 | 
```