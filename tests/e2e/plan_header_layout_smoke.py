from pathlib import Path

from playwright.sync_api import expect, sync_playwright


OUTPUT_DIR = Path("tests/e2e/artifacts")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def main() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1400})
        page.goto("http://localhost:5173", wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle")

        page.get_by_role("button", name="训练计划").click()
        page.wait_for_load_state("networkidle")

        monday_card = page.locator("article").filter(has=page.get_by_text("周一", exact=True)).first
        tuesday_card = page.locator("article").filter(has=page.get_by_text("周二", exact=True)).first

        page.get_by_text("周二", exact=True).wait_for()
        expect(monday_card.get_by_text("已排 1 个动作")).to_be_visible()
        expect(tuesday_card.get_by_text("已排 1 个动作")).to_have_count(0)
        expect(page.get_by_text("训练类型", exact=True)).to_have_count(0)
        expect(page.get_by_text("manual_strength", exact=True)).to_have_count(0)

        page.screenshot(path=str(OUTPUT_DIR / "plan-header-layout-full.png"), full_page=True)
        browser.close()


if __name__ == "__main__":
    main()
