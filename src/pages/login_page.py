"""로그인 페이지 동작."""
from __future__ import annotations

from locators.login_locators import LoginLocators
from pages.base_page import BasePage


class LoginPage(BasePage):
    def open(self) -> None:
        self.goto("/")

    def login(self, *, username: str, password: str) -> None:
        self.fill(LoginLocators.USERNAME, username)
        self.fill(LoginLocators.PASSWORD, password)
        self.click(LoginLocators.LOGIN_BUTTON)

    def has_error(self) -> bool:
        return self.is_visible(LoginLocators.ERROR)

    def error_message(self) -> str:
        return self.inner_text(LoginLocators.ERROR)
