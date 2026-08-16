"""체크아웃(결제 정보·완료) 페이지 Locator."""
from __future__ import annotations


class CheckoutLocators:
    FIRST_NAME = "[data-test='firstName']"
    LAST_NAME = "[data-test='lastName']"
    POSTAL_CODE = "[data-test='postalCode']"
    CONTINUE = "[data-test='continue']"
    FINISH = "[data-test='finish']"
    COMPLETE_HEADER = "[data-test='complete-header']"
