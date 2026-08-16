"""인증 Flow — 여러 Page 동작을 조합하는 비즈니스 로직 레이어.

Flow는 assertion 을 하지 않는다 (검증은 tests/ 책임). 결과 Page 객체를 반환한다.
"""
from __future__ import annotations

from playwright.sync_api import Page

from pages.inventory_page import InventoryPage
from pages.login_page import LoginPage


def login_as(page: Page, *, base_url: str, timeout: int, username: str, password: str) -> InventoryPage:
    """로그인 수행 후 상품 목록 페이지 객체를 반환."""
    login_page = LoginPage(page, base_url, timeout)
    login_page.open()
    login_page.login(username=username, password=password)
    return InventoryPage(page, base_url, timeout)
