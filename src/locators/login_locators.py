"""로그인 페이지 Locator — data-test 속성 우선 (UI 변경에 강함)."""
from __future__ import annotations


class LoginLocators:
    USERNAME = "[data-test='username']"
    PASSWORD = "[data-test='password']"
    LOGIN_BUTTON = "[data-test='login-button']"
    ERROR = "[data-test='error']"
