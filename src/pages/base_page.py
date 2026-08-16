"""모든 Page 객체의 공통 동작.

4-Layer 경계: Page는 '페이지 단위 동작'만 캡슐화한다.
- selector 는 locators/ 에서 주입받는다 (Page에 직접 박지 않음)
- 비즈니스 로직(여러 페이지 조합)은 flows/ 책임 — 여기서 하지 않음
- assertion 은 tests/ 책임 — 여기서 하지 않음
"""
from __future__ import annotations

from playwright.sync_api import Page, expect


class BasePage:
    def __init__(self, page: Page, base_url: str, default_timeout: int) -> None:
        self.page = page
        self.base_url = base_url
        self.default_timeout = default_timeout

    def goto(self, path: str = "") -> None:
        self.page.goto(f"{self.base_url}{path}", wait_until="domcontentloaded")

    def click(self, selector: str) -> None:
        self.page.locator(selector).click(timeout=self.default_timeout)

    def fill(self, selector: str, value: str) -> None:
        self.page.locator(selector).fill(value, timeout=self.default_timeout)

    def inner_text(self, selector: str) -> str:
        return self.page.locator(selector).inner_text(timeout=self.default_timeout)

    def count(self, selector: str) -> int:
        return self.page.locator(selector).count()

    def is_visible(self, selector: str) -> bool:
        # 단순 존재(count)가 아니라 가시성으로 판단 — CI headless 오탐 방지
        return self.page.locator(selector).is_visible()

    def expect_visible(self, selector: str) -> None:
        expect(self.page.locator(selector)).to_be_visible(timeout=self.default_timeout)
