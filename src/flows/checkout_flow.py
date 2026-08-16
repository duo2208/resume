"""체크아웃 Flow — 상품 담기 → 장바구니 → 결제정보 → 완료까지 조합."""
from __future__ import annotations

from playwright.sync_api import Page

from pages.cart_page import CartPage
from pages.checkout_page import CheckoutPage
from pages.inventory_page import InventoryPage


def checkout_single_item(
    page: Page,
    *,
    base_url: str,
    timeout: int,
    customer: dict,
) -> CheckoutPage:
    """로그인된 상태에서 상품 1개를 담아 체크아웃 완료까지 진행, CheckoutPage 반환."""
    inventory = InventoryPage(page, base_url, timeout)
    inventory.add_backpack_to_cart()
    inventory.open_cart()

    cart = CartPage(page, base_url, timeout)
    cart.proceed_to_checkout()

    checkout = CheckoutPage(page, base_url, timeout)
    checkout.fill_information(
        first_name=customer["first_name"],
        last_name=customer["last_name"],
        postal_code=customer["postal_code"],
    )
    checkout.finish()
    return checkout
