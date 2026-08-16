"""allure generate 직후 호출 — 커스텀 브랜딩 + 요약 대시보드 주입.

1) src/config/allure/custom-logo/{styles.css,failures.css} → report/plugin/custom-logo/
2) overview.html 생성 (generate_report)
3) index.html: CSS link 주입 + 커스텀 사이드바 오버레이 + 빈 hash → overview.html 리다이렉트
   (Allure 원본을 보려면 ?keepAllure=1)

사용: python scripts/apply_branding.py <report_dir> <results_dir>
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_report import generate as generate_overview  # noqa: E402

ASSETS = Path(__file__).resolve().parent.parent / "src" / "config" / "allure" / "custom-logo"
TITLE = "E2E Sample 리포트"

SIDEBAR_OVERLAY = """
  <aside class="app-side-nav" id="injected-sidebar">
    <div class="app-side-nav__head">
      <div class="app-side-nav__logo" style="font-size:34px;line-height:1">🤖</div>
      <div class="app-side-nav__title">QA E2E Automation</div>
    </div>
    <nav class="app-side-nav__menu">
      <a class="app-side-nav__link app-side-nav__link--active" href="overview.html"><span class="app-side-nav__icon">🏠</span><span>요약</span></a>
      <a class="app-side-nav__link" href="failures.html"><span class="app-side-nav__icon">🚩</span><span>실패 로그</span></a>
      <a class="app-side-nav__link" href="trends.html"><span class="app-side-nav__icon">📈</span><span>추이</span></a>
      <a class="app-side-nav__link" href="timeline.html"><span class="app-side-nav__icon">🕐</span><span>타임라인</span></a>
      <a class="app-side-nav__link" href="test-cases.html"><span class="app-side-nav__icon">💼</span><span>테스트 케이스</span></a>
    </nav>
  </aside>
<style id="injected-style">
.side-nav { display:none !important; }
.app { display:block !important; }
.app__content { margin-left:220px !important; min-height:100vh !important; position:relative !important; overflow:auto !important; }
</style>
<script id="injected-redirect">
(function(){
  function go(){ if(location.search.indexOf("keepAllure=1")>=0)return;
    var h=location.hash||""; if(h!==""&&h!=="#")return;
    var base=location.href.split("#")[0].split("?")[0].replace(/index\\.html$/,""); location.replace(base+"overview.html"); }
  window.addEventListener("hashchange",go); go();
})();
</script>
"""


def apply(report_dir: Path, results_dir: Path) -> None:
    if not report_dir.is_dir():
        raise SystemExit(f"report dir 없음: {report_dir}")

    plugin = report_dir / "plugin" / "custom-logo"
    plugin.mkdir(parents=True, exist_ok=True)
    for asset in ("styles.css", "failures.css"):
        src = ASSETS / asset
        if src.exists():
            shutil.copy(src, plugin / asset)

    try:
        generate_overview(str(results_dir), str(report_dir))
    except Exception as error:
        print(f"[overview skip] {type(error).__name__}: {error}")

    index = report_dir / "index.html"
    if not index.exists():
        return
    content = index.read_text(encoding="utf-8")
    content = content.replace('lang="en"', 'lang="ko"')
    content = re.sub(r"<title>.*?</title>", f"<title>{TITLE}</title>", content, count=1)
    for link in (
        '<link rel="stylesheet" type="text/css" href="plugin/custom-logo/styles.css">',
        '<link rel="stylesheet" type="text/css" href="plugin/custom-logo/failures.css">',
    ):
        if link not in content:
            content = content.replace("</head>", f"  {link}\n</head>")
    for marker in ("injected-sidebar", "injected-style", "injected-redirect"):
        content = re.sub(
            r'<(aside|style|script)[^>]*id="' + marker + r'"[^>]*>.*?</\1>',
            "",
            content,
            flags=re.DOTALL,
        )
    content = content.replace("<body>", "<body>\n" + SIDEBAR_OVERLAY)
    index.write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply branding + custom overview to Allure report.")
    parser.add_argument("report_dir", type=Path)
    parser.add_argument("results_dir", type=Path)
    args = parser.parse_args()
    apply(args.report_dir, args.results_dir)
    print("[apply_branding] 완료")
    return 0


if __name__ == "__main__":
    sys.exit(main())
