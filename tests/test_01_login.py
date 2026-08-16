"""로그인 — 핵심 경로(P0). 모든 TC 는 Arrange-Act-Assert 구조."""
from __future__ import annotations

import allure
import pytest

from flows.auth_flow import login_as
from pages.login_page import LoginPage


@allure.feature("인증")
class TestLogin:
    @pytest.mark.p0
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.story("로그인 성공")
    @allure.title("표준 사용자 로그인 성공 → 상품 목록 진입")
    def test_standard_login(self, page, config):
        # Arrange
        user = config["users"]["standard"]
        # Act
        inventory = login_as(
            page,
            base_url=config["base_url"],
            timeout=config["default_wait_timeout"],
            username=user["username"],
            password=user["password"],
        )
        # Assert
        assert inventory.is_loaded()

    @pytest.mark.p0
    @allure.severity(allure.severity_level.NORMAL)
    @allure.story("로그인 실패")
    @allure.title("잘못된 비밀번호 → 에러 메시지 노출")
    def test_login_invalid_password(self, page, config):
        # Arrange
        login_page = LoginPage(page, config["base_url"], config["default_wait_timeout"])
        login_page.open()
        # Act
        login_page.login(
            username=config["users"]["standard"]["username"], password="wrong_password"
        )
        # Assert
        assert login_page.has_error()

    @pytest.mark.p1
    @allure.severity(allure.severity_level.NORMAL)
    @allure.story("로그인 실패")
    @allure.title("잠긴 계정(locked_out) → 차단 에러 노출")
    def test_locked_out_user(self, page, config):
        # Arrange
        locked = config["users"]["locked_out"]
        login_page = LoginPage(page, config["base_url"], config["default_wait_timeout"])
        login_page.open()
        # Act
        login_page.login(username=locked["username"], password=locked["password"])
        # Assert
        assert login_page.has_error()
