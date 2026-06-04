from pathlib import Path

from playwright.sync_api import sync_playwright


OUTPUT_DIR = Path("tests/e2e/artifacts")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def main() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1400})
        page.goto("http://localhost:5173", wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle")

        page.get_by_role("button", name="我的档案").click()
        page.wait_for_load_state("networkidle")

        hero = page.locator("section").filter(has=page.get_by_text("我的档案")).first
        hero_screenshot = OUTPUT_DIR / "profile-tab-hero.png"
        hero.screenshot(path=str(hero_screenshot))

        summary_cards = hero.locator("article")
        summary_count = summary_cards.count()
        assert summary_count == 4, f"expected 4 summary cards, got {summary_count}"

        panel_button = page.get_by_role("button", name="数据管理")
        assert panel_button.get_attribute("aria-expanded") == "false"
        panel_button.click()
        assert panel_button.get_attribute("aria-expanded") == "true"
        page.get_by_text("后端导入只会同步").wait_for()

        weight_input = page.get_by_label("当前体重 (kg)")
        weight_input.fill("")
        page.wait_for_timeout(250)

        weight_value = summary_cards.nth(0).locator("p").nth(1).inner_text()
        assert weight_value == "未填写"

        page.screenshot(path=str(OUTPUT_DIR / "profile-tab-full.png"), full_page=True)
        browser.close()


if __name__ == "__main__":
    main()
