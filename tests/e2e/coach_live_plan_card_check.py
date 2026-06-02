from __future__ import annotations

from playwright.sync_api import expect, sync_playwright


APP_URL = "http://127.0.0.1:5173"


def main() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 960})

        page.goto(APP_URL, wait_until="networkidle")
        page.get_by_role("button", name="AI 教练").click()

        composer = page.locator("textarea").first
        expect(composer).to_be_visible(timeout=10_000)
        composer.fill("为周一休息日设计一份有氧+核心运动计划，然后生成计划修改卡")
        page.keyboard.press("Enter")

        expect(page.get_by_text("思考中")).to_be_visible(timeout=10_000)
        adopt_buttons = page.get_by_role("button", name="采纳并更新计划")
        dismiss_buttons = page.get_by_role("button", name="忽略")
        expect(adopt_buttons.last).to_be_visible(timeout=60_000)
        expect(dismiss_buttons.last).to_be_visible(timeout=10_000)

        browser.close()


if __name__ == "__main__":
    main()
