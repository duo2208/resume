"""데모용 합성(Sample) allure-results + 부가 데이터 생성 — 대시보드 시연 전용.

⚠️ 전부 가짜 데이터(saucedemo 도메인). 실제 결과/회사 정보 없음.
생성물:
  - <results>/seed-*-result.json   (스텝 포함)
  - <results>/environment.properties, executor.json
  - <results>/flaky_history_qa.json (추이용 — 최근 10 런)
  - <results>/diagnose/_accuracy.json (AI 진단 정확도용)

사용: python scripts/seed_mock_data.py [results-dir]   # 기본: allure-results
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BASE = 1_780_000_000_000  # 고정 epoch(ms)

# (id, feature, 이름, status, severity, duration_ms, ai_note, trace)
CASES = [
    ("DEMO-AUTH-001", "인증", "표준 사용자 로그인 성공", "passed", "critical", 2400, "", ""),
    ("DEMO-AUTH-002", "인증", "잘못된 비밀번호 에러 노출", "passed", "normal", 1800, "", ""),
    ("DEMO-AUTH-003", "인증", "잠긴 계정 차단 메시지", "passed", "normal", 1600, "", ""),
    ("DEMO-AUTH-009", "인증", "SSO 로그인 (외부 연동)", "skipped", "minor", 0,
     "", "[sample] 사전 조건 미충족 — 외부 SSO 환경 없음"),
    ("DEMO-CART-001", "장바구니", "상품 담기 → 배지 1 증가", "passed", "critical", 2100, "", ""),
    ("DEMO-CART-002", "장바구니", "상품 제거 → 배지 0 복귀", "passed", "normal", 1900, "", ""),
    ("DEMO-CART-003", "장바구니", "여러 상품 담기 수량 합산", "passed", "normal", 2600, "", ""),
    ("DEMO-CART-004", "장바구니", "장바구니 배지 갱신 타이밍", "broken", "normal", 5200,
     "⏱️ Timing/flaky (82%) → 명시적 wait 누락 의심, 배지 렌더 전 assert",
     "playwright._impl._errors.TimeoutError: locator.inner_text: Timeout 10000ms exceeded.\n  waiting for [data-test='shopping-cart-badge']"),
    ("DEMO-SEARCH-001", "검색", "키워드 검색 결과 노출", "passed", "normal", 2200, "", ""),
    ("DEMO-SEARCH-002", "검색", "검색 결과 정렬 (가격 낮은순)", "passed", "minor", 2700, "", ""),
    ("DEMO-SEARCH-003", "검색", "자동완성 추천", "failed", "normal", 1500,
     "🔌 API contract (90%) → /suggest 응답 스키마 변경 감지 (items[].label 누락)",
     "AssertionError: expected key 'label' in suggestion item\n  assert 'label' in {'id': 1, 'text': '...'}"),
    ("DEMO-DETAIL-001", "작품상세", "상세 페이지 로드", "passed", "normal", 3100, "", ""),
    ("DEMO-DETAIL-002", "작품상세", "관련 상품 캐러셀 렌더", "passed", "minor", 4800, "", ""),
    ("DEMO-DETAIL-009", "작품상세", "이미지 lazy-load 스크롤", "passed", "minor", 9300, "", ""),
    ("DEMO-PAY-001", "결제", "결제 정보 입력 단계 진입", "passed", "critical", 2900, "", ""),
    ("DEMO-PAY-002", "결제", "주문 완료 E2E", "passed", "blocker", 8700, "", ""),
    ("DEMO-PAY-006", "결제", "쿠폰 적용 후 금액 갱신", "failed", "critical", 3400,
     "🎯 Locator drift (88%) → 쿠폰 input 셀렉터 변경, data-test 기반으로 교체 권장",
     "playwright._impl._errors.Error: locator resolved to hidden element\n  <input class='coupon-old'>"),
    ("DEMO-CHECKOUT-001", "체크아웃", "배송지 입력 검증", "passed", "normal", 2500, "", ""),
    ("DEMO-CHECKOUT-002", "체크아웃", "결제 수단 선택", "broken", "critical", 6100,
     "🌐 Environment (75%) → 결제 모듈 네트워크 타임아웃, 재시도 권장",
     "playwright._impl._errors.TimeoutError: page.wait_for_url: Timeout exceeded.\n  waiting for navigation to '**/complete'"),
    ("DEMO-NAV-001", "네비게이션", "햄버거 메뉴 열기/닫기", "passed", "minor", 1400, "", ""),
    ("DEMO-NAV-002", "네비게이션", "로그아웃 후 홈 이동", "passed", "normal", 1700, "", ""),
    ("DEMO-NAV-003", "네비게이션", "뒤로가기 상태 유지", "passed", "minor", 1300, "", ""),
    ("DEMO-MEMBER-001", "멤버십", "플랜 선택 화면", "passed", "normal", 2300, "", ""),
    ("DEMO-MEMBER-002", "멤버십", "결제 팝업 오픈", "passed", "normal", 3600, "", ""),
    ("DEMO-MEMBER-007", "멤버십", "자동 갱신 안내 모달", "skipped", "minor", 0,
     "", "[sample] 사전 조건 미충족 — 갱신 대상 계정 없음"),
    ("DEMO-EVENT-001", "이벤트", "이벤트 배너 노출", "passed", "minor", 1500, "", ""),
    ("DEMO-EVENT-002", "이벤트", "쿠폰 발급 플로우", "passed", "normal", 2800, "", ""),
    ("DEMO-PERF-001", "성능", "홈 초기 렌더 < 3s", "passed", "normal", 2950, "", ""),
]


def _steps(case_status: str, name: str, start: int, dur: int) -> list[dict]:
    """AAA 스텝 3개. 실패/깨짐이면 마지막 Assert 스텝이 그 상태."""
    seg = max(dur // 3, 1)
    plan = [
        ("Arrange — 테스트 계정·상태 준비", "passed"),
        (f"Act — {name}", "passed" if case_status != "broken" else "broken"),
        ("Assert — 결과 검증", "passed" if case_status == "passed" else case_status),
    ]
    steps = []
    t = start
    for step_name, st in plan:
        steps.append({"name": step_name, "status": st, "time": {"start": t, "stop": t + seg, "duration": seg}})
        t += seg
    return steps


def seed(results_dir: str) -> int:
    out = Path(results_dir)
    out.mkdir(parents=True, exist_ok=True)
    workers = ["gw0", "gw1", "gw2"]
    clocks = {w: BASE for w in workers}

    for i, (tid, feature, name, status, severity, dur, note, trace) in enumerate(CASES):
        worker = workers[i % len(workers)]
        start = clocks[worker]
        stop = start + dur
        clocks[worker] = stop + 50

        result = {
            "name": f"{tid}: {name}",
            "fullName": f"sample.{feature}.{tid}",
            "status": status,
            "start": start,
            "stop": stop,
            "steps": _steps(status, name, start, dur),
            "labels": [
                {"name": "feature", "value": feature},
                {"name": "severity", "value": severity},
                {"name": "thread", "value": worker},
            ],
        }
        if note:
            result["description"] = note
        if trace:
            result["statusDetails"] = {"message": trace.splitlines()[0], "trace": trace}
        (out / f"seed-{i:03d}-result.json").write_text(
            json.dumps(result, ensure_ascii=False), encoding="utf-8"
        )

    (out / "environment.properties").write_text(
        "Target=saucedemo.com\nBrowser=Chromium (Playwright)\n"
        "Framework=pytest + Playwright\nData=Sample (데모용 합성 데이터)\n",
        encoding="utf-8",
    )
    (out / "executor.json").write_text(
        json.dumps({"name": "Sample", "type": "local", "reportName": "E2E MockUp 리포트"}, ensure_ascii=False),
        encoding="utf-8",
    )

    # --- 추이: flaky_history (최근 10 런) ---
    flaky_tests = ["DEMO-CART-004 장바구니 배지 갱신 타이밍", "DEMO-PAY-006 쿠폰 적용 후 금액 갱신",
                   "DEMO-CHECKOUT-002 결제 수단 선택", "DEMO-SEARCH-003 자동완성 추천"]
    # 각 런의 실패 목록 (간헐 패턴)
    fail_pattern = [
        [flaky_tests[0]],
        [flaky_tests[0], flaky_tests[2]],
        [],
        [flaky_tests[1]],
        [flaky_tests[0], flaky_tests[1]],
        [flaky_tests[2]],
        [],
        [flaky_tests[0]],
        [flaky_tests[1], flaky_tests[3]],
        [flaky_tests[0], flaky_tests[2]],
    ]
    history = [
        {"run_index": idx + 1, "timestamp": f"2026-06-0{(idx % 7) + 1}T09:00:00", "failures": fails}
        for idx, fails in enumerate(fail_pattern)
    ]
    (out / "flaky_history_qa.json").write_text(json.dumps(history, ensure_ascii=False), encoding="utf-8")

    # --- AI 진단 정확도 ---
    accuracy = {
        "match_coarse_rate": 0.86,
        "match_fine_rate": 0.74,
        "action_helpful_rate": 0.68,
        "unrecorded_rate": 0.12,
        "total_predictions": 50,
        "total_recorded": 44,
        "confusion_fine": {"timing → environment": 4, "locator_drift → api_contract": 2, "test_data → timing": 1},
        "per_run": [
            {"run_id": f"2026-06-{d:02d}", "recorded": r, "fine_correct": c}
            for d, r, c in [(1, 5, 3), (2, 6, 4), (3, 4, 3), (4, 7, 5), (5, 6, 5), (6, 8, 6), (7, 8, 7)]
        ],
        "generated_at": "2026-06-08T09:00:00",
    }
    diag_dir = out / "diagnose"
    diag_dir.mkdir(parents=True, exist_ok=True)
    (diag_dir / "_accuracy.json").write_text(json.dumps(accuracy, ensure_ascii=False), encoding="utf-8")

    return len(CASES)


def main() -> int:
    results_dir = sys.argv[1] if len(sys.argv) > 1 else "allure-results"
    n = seed(results_dir)
    print(f"[seed_mock_data] {n}건 합성 결과 + flaky history + 진단 정확도 생성 → {results_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
