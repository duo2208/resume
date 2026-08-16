"""pytest 전역 설정 — 브라우저 fixture · 실패 시 스크린샷 → Allure 첨부.

테스트 독립성: 매 테스트마다 새 browser context 로 상태를 격리한다.
세션 종료 시 Allure 메타(environment·categories·executor)를 results 에 주입해
기본 리포트를 '운영 대시보드'처럼 보강한다.
"""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import allure
import pytest
from playwright.sync_api import Page, sync_playwright

from utils.config import load_config

ALLURE_DIR = Path("allure-results")
BASE_DIR = Path(__file__).resolve().parent.parent


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--headed-mode", action="store_true", default=False, help="브라우저 화면 표시(디버깅용)"
    )


@pytest.fixture(scope="session")
def config() -> dict:
    return load_config()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call):
    """각 단계 결과를 item 에 저장 — fixture teardown 에서 실패 여부 판단용."""
    outcome = yield
    report = outcome.get_result()
    setattr(item, f"rep_{report.when}", report)


@pytest.fixture
def page(request: pytest.FixtureRequest, config: dict) -> Page:
    headed = request.config.getoption("--headed-mode")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=not headed)
        context = browser.new_context()
        page = context.new_page()
        page.set_default_timeout(config["default_wait_timeout"])
        try:
            yield page
        finally:
            report = getattr(request.node, "rep_call", None)
            if report is not None and report.failed:
                _attach_failure_screenshot(page, request.node.name)
            context.close()
            browser.close()


def _attach_failure_screenshot(page: Page, test_name: str) -> None:
    """실패 시 전체 화면 스크린샷을 Allure 에 첨부. (진단 보조라 실패해도 무시)"""
    try:
        screenshot = page.screenshot(full_page=True)
        allure.attach(
            screenshot, name=f"failure-{test_name}", attachment_type=allure.attachment_type.PNG
        )
    except Exception as error:
        print(f"[screenshot skip] {type(error).__name__}: {error}")


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Allure 리포트 보강용 메타 파일을 allure-results 에 주입.

    - environment.properties : 환경 위젯
    - categories.json        : 커스텀 결함 분류 위젯
    - executor.json          : CI 빌드 링크 (GitHub Actions 에서만)
    """
    if not ALLURE_DIR.exists():
        return

    (ALLURE_DIR / "environment.properties").write_text(
        "Target=saucedemo.com\n"
        "Browser=Chromium (Playwright)\n"
        "Framework=pytest + Playwright\n"
        "Architecture=POM 4-Layer (locators/pages/flows/tests)\n",
        encoding="utf-8",
    )

    categories_src = BASE_DIR / "allure" / "categories.json"
    if categories_src.exists():
        shutil.copy(categories_src, ALLURE_DIR / "categories.json")

    run_id = os.environ.get("GITHUB_RUN_ID")
    executor = {
        "name": "GitHub Actions" if run_id else "Local",
        "type": "github" if run_id else "local",
        "reportName": "QA E2E Automation Report",
    }
    if run_id:
        server = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
        repo = os.environ.get("GITHUB_REPOSITORY", "")
        executor["buildName"] = f"Run #{os.environ.get('GITHUB_RUN_NUMBER', '')}"
        executor["buildUrl"] = f"{server}/{repo}/actions/runs/{run_id}"
    (ALLURE_DIR / "executor.json").write_text(
        json.dumps(executor, ensure_ascii=False), encoding="utf-8"
    )
