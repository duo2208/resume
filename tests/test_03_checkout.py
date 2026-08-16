"""체크아웃 — 로그인~주문완료 E2E(P0). Flow 조합 검증."""
from __future__ import annotations

import allure
import pytest

from flows.auth_flow import login_as
from flows.checkout_flow import checkout_single_item


@allure.feature("체크아웃")
class TestCheckout:
    @pytest.mark.p0
    @allure.severity(allure.severity_level.BLOCKER)
    @allure.story("주문 완료 E2E")
    @allure.title("로그인 → 상품 담기 → 결제정보 입력 → 주문 완료")
    def test_full_checkout(self, page, config):
        # Arrange
        user = config["users"]["standard"]
        login_as(
            page,
            base_url=config["base_url"],
            timeout=config["default_wait_timeout"],
            username=user["username"],
            password=user["password"],
        )
        # Act
        checkout = checkout_single_item(
            page,
            base_url=config["base_url"],
            timeout=config["default_wait_timeout"],
            customer=config["customer"],
        )
        # Assert
        assert checkout.is_complete()
