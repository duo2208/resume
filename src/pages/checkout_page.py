"""체크아웃 페이지 동작 (배송정보 입력 → 완료)."""
from __future__ import annotations

from locators.checkout_locators import CheckoutLocators
from pages.base_page import BasePage


class CheckoutPage(BasePage):
    def fill_information(self, *, first_name: str, last_name: str, postal_code: str) -> None:
        self.fill(CheckoutLocators.FIRST_NAME, first_name)
        self.fill(CheckoutLocators.LAST_NAME, last_name)
        self.fill(CheckoutLocators.POSTAL_CODE, postal_code)
        self.click(CheckoutLocators.CONTINUE)

    def finish(self) -> None:
        self.click(CheckoutLocators.FINISH)

    def is_complete(self) -> bool:
        return self.is_visible(CheckoutLocators.COMPLETE_HEADER)
