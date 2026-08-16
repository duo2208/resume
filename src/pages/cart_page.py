"""장바구니 페이지 동작."""
from __future__ import annotations

from locators.cart_locators import CartLocators
from pages.base_page import BasePage


class CartPage(BasePage):
    def item_count(self) -> int:
        return self.count(CartLocators.ITEM)

    def proceed_to_checkout(self) -> None:
        self.click(CartLocators.CHECKOUT)
