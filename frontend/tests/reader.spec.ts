import { test, expect } from "@playwright/test";

test("prepared sample has a labeled answer and clickable evidence", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "A passage is just the beginning." }),
  ).toBeVisible();
  await page.getByRole("button", { name: "How do trees cool cities?" }).click();
  await expect(
    page.getByText("Prepared demo • no external calls"),
  ).toBeVisible();
  await page.locator(".answer-text").getByRole("link", { name: "[1]" }).click();
  await page.getByText("[1] EPA:", { exact: false }).click();
  await expect(page.getByRole("link", { name: "Open source" })).toHaveAttribute(
    "href",
    /epa.gov/,
  );
});

test("arbitrary input is illustrative and unsafe HTML is not rendered", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Paste text", exact: true }).click();
  await page
    .getByLabel("Plain text or Markdown")
    .fill('# My notes\n\n**Bold idea** with <img src=x onerror="alert(1)">');
  await page.getByRole("button", { name: "Open in reader" }).click();
  await expect(page.locator("article strong")).toHaveText("Bold idea");
  await expect(page.locator("article img")).toHaveCount(0);
  await page.getByLabel("What are you curious about?").fill("Explain the idea");
  await page.getByRole("button", { name: "Explore demo answer" }).click();
  await expect(
    page.getByText("Illustrative demo • not document-grounded"),
  ).toBeVisible();
});

test("keyboard selection populates the passage and live failure stays explicit", async ({
  page,
}) => {
  await page.goto("/");
  await page.locator("article").evaluate((el) => {
    const range = document.createRange();
    range.selectNodeContents(el.querySelector("p")!);
    window.getSelection()!.removeAllRanges();
    window.getSelection()!.addRange(range);
    el.dispatchEvent(new KeyboardEvent("keyup", { bubbles: true }));
  });
  await expect(page.getByLabel("Selected passage")).toHaveValue(/Urban trees/);
  await page.getByRole("button", { name: "Live RAG", exact: true }).click();
  await page
    .getByLabel("What are you curious about?")
    .fill("How do trees cool?");
  await page.getByRole("button", { name: "Search & answer" }).click();
  await expect(page.getByRole("alert")).toContainText("TAVILY_API_KEY");
  await expect(page.locator(".answer")).toHaveCount(0);
});

test("mobile fits the viewport", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(
    page.getByRole("button", { name: "Demo responses", exact: true }),
  ).toBeVisible();
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(390);
});

test("PDF uploads into the reader and original fallback keeps the question box", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Upload PDF", exact: true }).click();
  await page
    .getByLabel("Selectable-text PDF", { exact: true })
    .setInputFiles("../tests/fixtures/trees.pdf");
  await expect(page.locator("article")).toContainText(
    "Trees cool cities through shade and evaporation.",
  );
  await page.getByRole("button", { name: "Original PDF" }).click();
  await expect(page.getByTitle("Original PDF")).toBeVisible();
  await expect(
    page.getByText("Original PDF fallback.", { exact: false }),
  ).toBeVisible();
  await expect(page.getByLabel("What are you curious about?")).toBeVisible();
  await page.getByRole("button", { name: "Formatted text" }).click();
  await expect(page.locator("article")).toContainText("Trees cool cities");
});
