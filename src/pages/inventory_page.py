"""상품 목록(인벤토리) 페이지 동작."""
from __future__ import annotations

from locators.inventory_locators import InventoryLocators
from pages.base_page import BasePage


class InventoryPage(BasePage):
    def is_loaded(self) -> bool:
        return self.is_visible(InventoryLocators.CONTAINER)

    def item_count(self) -> int:
        return self.count(InventoryLocators.ITEM)

    def add_backpack_to_cart(self) -> None:
        self.click(InventoryLocators.ADD_BACKPACK)

    def remove_backpack_from_cart(self) -> None:
        self.click(InventoryLocators.REMOVE_BACKPACK)

    def cart_count(self) -> int:
        if not self.is_visible(InventoryLocators.CART_BADGE):
            return 0
        return int(self.inner_text(InventoryLocators.CART_BADGE))

    def open_cart(self) -> None:
        self.click(InventoryLocators.CART_LINK)
