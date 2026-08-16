"""상품 목록(인벤토리) 페이지 Locator."""
from __future__ import annotations


class InventoryLocators:
    CONTAINER = "[data-test='inventory-container']"
    ITEM = ".inventory_item"
    ADD_BACKPACK = "[data-test='add-to-cart-sauce-labs-backpack']"
    REMOVE_BACKPACK = "[data-test='remove-sauce-labs-backpack']"
    CART_LINK = "[data-test='shopping-cart-link']"
    CART_BADGE = "[data-test='shopping-cart-badge']"
