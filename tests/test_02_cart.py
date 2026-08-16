"""장바구니 — 담기/제거/배지 수량(P0)."""
from __future__ import annotations

import allure
import pytest

from flows.auth_flow import login_as


@allure.feature("장바구니")
class TestCart:
    def _login(self, page, config):
        user = config["users"]["standard"]
        return login_as(
            page,
            base_url=config["base_url"],
            timeout=config["default_wait_timeout"],
            username=user["username"],
            password=user["password"],
        )

    @pytest.mark.p0
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.story("담기")
    @allure.title("상품 담기 → 장바구니 배지 수량 1 증가")
    def test_add_to_cart_updates_badge(self, page, config):
        # Arrange
        inventory = self._login(page, config)
        assert inventory.cart_count() == 0
        # Act
        inventory.add_backpack_to_cart()
        # Assert
        assert inventory.cart_count() == 1

    @pytest.mark.p1
    @allure.severity(allure.severity_level.NORMAL)
    @allure.story("제거")
    @allure.title("담은 상품 제거 → 배지 수량 0 복귀")
    def test_remove_from_cart_resets_badge(self, page, config):
        # Arrange
        inventory = self._login(page, config)
        inventory.add_backpack_to_cart()
        assert inventory.cart_count() == 1
        # Act
        inventory.remove_backpack_from_cart()
        # Assert
        assert inventory.cart_count() == 0
