"""allure-results → 커스텀 멀티 페이지 리포트 생성.

`src/config/allure/custom-logo/failures.css` 클래스 사용. 그룹은 `feature` 라벨.
페이지: overview / failures(master-detail+스텝표) / trends(AI 진단 정확도+차트) /
       timeline(워커 Gantt) / test-cases(필터+목록).  내부 의존성 없음.

사용: python scripts/generate_report.py <allure-results-dir> <report-dir>
"""
from __future__ import annotations

import glob
import html
import json
import math
import sys
from collections import Counter
from pathlib import Path

_SEV_ORDER = {"blocker": 0, "critical": 1, "normal": 2, "minor": 3, "trivial": 4}
_ICON = {"passed": "✅", "failed": "❌", "broken": "⚠️", "skipped": "⏭️", "unknown": "❔"}
_TEXT = {"passed": "SUCCESS", "failed": "FAILURE", "broken": "BROKEN", "skipped": "SKIPPED", "unknown": "UNKNOWN"}

_NAV = [
    ("overview", "🏠", "요약", "overview.html"),
    ("failures", "🚩", "실패 로그", "failures.html"),
    ("trends", "📈", "추이", "trends.html"),
    ("timeline", "🕐", "타임라인", "timeline.html"),
    ("tests", "💼", "테스트 케이스", "test-cases.html"),
]


def _load(results_dir: str) -> list[dict]:
    items: list[dict] = []
    for path in glob.glob(str(Path(results_dir) / "*-result.json")):
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        labels = {l.get("name"): l.get("value") for l in data.get("labels", [])}
        start, stop = data.get("start"), data.get("stop")
        duration = (stop - start) if isinstance(start, int) and isinstance(stop, int) else 0
        details = data.get("statusDetails") or {}
        items.append({
            "uid": Path(path).stem.replace("-result", ""),
            "name": data.get("name", ""),
            "status": data.get("status", "unknown"),
            "start": start, "stop": stop, "duration": duration,
            "feature": labels.get("feature", "기타"),
            "severity": labels.get("severity", ""),
            "thread": labels.get("thread", "gw0"),
            "steps": data.get("steps", []),
            "message": (details.get("message") or "").strip(),
            "trace": (details.get("trace") or "").strip(),
            "description": (data.get("description") or "").strip(),
        })
    return items


def _fmt(ms: int | None) -> str:
    if not ms:
        return "0ms"
    if ms < 1000:
        return f"{int(ms)}ms"
    if ms < 60_000:
        return f"{ms / 1000:.2f}초"
    m, s = divmod(ms / 1000, 60)
    return f"{int(m)}분 {s:.1f}초"


def _read_env(results_dir: str) -> dict[str, str]:
    path = Path(results_dir) / "environment.properties"
    env: dict[str, str] = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def _read_executor(results_dir: str) -> dict:
    path = Path(results_dir) / "executor.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
    return {}


def _split_id(name: str) -> tuple[str, str]:
    if ":" in name:
        head, tail = name.split(":", 1)
        return head.strip(), tail.strip()
    return "", name


def _rate_class(rate: float) -> str:
    return "pass-rate-good" if rate >= 95 else "pass-rate-ok" if rate >= 80 else "pass-rate-poor"


def _sidebar(active: str) -> str:
    links = "".join(
        f'<a class="app-side-nav__link{" app-side-nav__link--active" if k == active else ""}" href="{href}">'
        f'<span class="app-side-nav__icon">{icon}</span><span>{label}</span></a>'
        for k, icon, label, href in _NAV
    )
    return (
        '<aside class="app-side-nav"><div class="app-side-nav__head">'
        '<div class="app-side-nav__logo" style="font-size:34px;line-height:1">🤖</div>'
        '<div class="app-side-nav__title">QA E2E Automation</div></div>'
        f'<nav class="app-side-nav__menu">{links}</nav></aside>'
    )


def _page(title: str, subtitle: str, body: str, active: str, *, head_extra: str = "", body_extra: str = "") -> str:
    return (
        '<!DOCTYPE html>\n<html lang="ko">\n<head>\n<meta charset="utf-8">\n'
        f'<title>{title} — E2E MockUp 리포트</title>\n'
        '<link rel="stylesheet" type="text/css" href="plugin/custom-logo/failures.css">\n'
        f'{head_extra}</head>\n<body class="page-{active}">\n{_sidebar(active)}\n'
        f'<main class="page">\n<header class="page-header"><div><h1>{title}</h1>'
        f'<p class="page-subtitle">{subtitle}</p></div></header>\n{body}\n</main>\n{body_extra}\n</body>\n</html>\n'
    )


_SAMPLE_BANNER = (
    '<p class="page-subtitle" style="margin-top:-18px;margin-bottom:20px;color:var(--primary)">'
    '📊 Sample data — 프레임워크 시연용 합성 데이터입니다.</p>'
)


def _mini_row(item: dict, *, show_severity: bool) -> str:
    icon = _ICON.get(item["status"], "❔")
    sev = item.get("severity", "")
    sev_chip = (f'<span class="chip chip-severity-{html.escape(sev)}">{html.escape(sev)}</span>'
                if show_severity and sev else "")
    _id, label = _split_id(item["name"])
    id_html = f'<span class="mini-id">{html.escape(_id)}</span>' if _id else ""
    return (
        f'<li class="mini-row card-{item["status"]}"><a class="mini-row__link" href="failures.html#{html.escape(item["uid"])}">'
        f'<span class="mini-status">{icon}</span>{sev_chip}{id_html}'
        f'<span class="mini-name">{html.escape(label)}</span>'
        f'<span class="mini-duration">{_fmt(item["duration"])}</span></a></li>'
    )


# ============================================================ step table / cards
def _step_table(steps: list[dict]) -> str:
    rows = []
    for i, s in enumerate(steps, start=1):
        st = s.get("status", "unknown")
        icon = _ICON.get(st, "❔")
        t = s.get("time") or {}
        rows.append(
            f'<tr class="row-{st}"><td class="col-step">{i}</td>'
            f'<td class="col-desc">{html.escape(s.get("name", "?"))}</td>'
            f'<td class="col-status"><span class="status-icon">{icon}</span>'
            f'<span class="status-text">{_TEXT.get(st, "UNKNOWN")}</span></td>'
            f'<td class="col-duration">{_fmt(t.get("duration", 0))}</td>'
            f'<td class="col-note">{html.escape((s.get("statusMessage") or "").splitlines()[0] if s.get("statusMessage") else "")}</td></tr>'
        )
    if not rows:
        rows.append('<tr><td colspan="5" class="empty">기록된 스텝 없음</td></tr>')
    return (
        '<table class="step-table"><thead><tr><th class="col-step">단계</th>'
        '<th class="col-desc">설명</th><th class="col-status">상태</th>'
        '<th class="col-duration">소요 시간</th><th class="col-note">비고</th></tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table>'
    )


def _test_card(item: dict, *, active: bool = False) -> str:
    _id, label = _split_id(item["name"])
    st = item["status"]
    icon = _ICON.get(st, "❔")
    sev = item.get("severity", "")
    chips = (f'<div class="card-chips"><span class="chip chip-severity-{html.escape(sev)}">{html.escape(sev)}</span></div>'
             if sev else "")
    note = (f'<div class="card-section card-section--heal"><h3 class="card-section__title">🤖 AI 진단</h3>'
            f'<p class="heal-p">{html.escape(item["description"])}</p></div>') if item.get("description") else ""
    trace_src = item.get("trace") or item.get("message")
    trace = (f'<details class="card-collapsible" open><summary>📜 에러 트레이스</summary>'
             f'<pre class="error-trace">{html.escape(trace_src)}</pre></details>') if trace_src else ""
    return (
        f'<section class="card card-{st}{" card--active" if active else ""}" data-uid="{html.escape(item["uid"])}">'
        f'<header class="card-header"><span class="card-icon">📝</span>'
        f'<span class="card-test-id">{html.escape(_id)}</span>'
        f'<span class="card-test-name">{html.escape(label)}</span>'
        f'<span class="card-status status-{st}">{icon} {_TEXT.get(st, "UNKNOWN")}</span>'
        f'<span class="card-duration">{_fmt(item["duration"])}</span></header>'
        f'{chips}{note}{_step_table(item.get("steps", []))}{trace}</section>'
    )


def _test_row(item: dict, *, active: bool = False) -> str:
    _id, label = _split_id(item["name"])
    icon = _ICON.get(item["status"], "❔")
    return (
        f'<button class="test-row card-{item["status"]}{" test-row--active" if active else ""}" '
        f'data-uid="{html.escape(item["uid"])}" data-group="{html.escape(item["feature"])}" type="button">'
        f'<span class="test-row-status">{icon}</span><span class="test-row-main">'
        f'<span class="test-row-id">{html.escape(_id)}</span>'
        f'<span class="test-row-name">{html.escape(label)}</span></span>'
        f'<span class="test-row-duration">{_fmt(item["duration"])}</span></button>'
    )


_INTERACTION_JS = """
<script>
(function(){
  var rows = Array.prototype.slice.call(document.querySelectorAll('.test-row'));
  var cards = Array.prototype.slice.call(document.querySelectorAll('.test-detail .card'));
  function select(uid){
    rows.forEach(function(r){ r.classList.toggle('test-row--active', r.dataset.uid === uid); });
    cards.forEach(function(c){ c.classList.toggle('card--active', c.dataset.uid === uid); });
  }
  rows.forEach(function(r){ r.addEventListener('click', function(){ select(r.dataset.uid); }); });
  function fromHash(){ var uid=(location.hash||'').slice(1); if(!uid)return false;
    var row=rows.filter(function(r){return r.dataset.uid===uid;})[0]; if(!row)return false;
    select(uid); if(row.scrollIntoView) row.scrollIntoView({block:'center'}); return true; }
  if (rows.length && !fromHash()) select(rows[0].dataset.uid);
  window.addEventListener('hashchange', fromHash);
  var sf='all', gf='all', gs=document.querySelector('.group-filter');
  function apply(){ var first=null;
    rows.forEach(function(r){ var sm=(sf==='all'||r.classList.contains('card-'+sf));
      var gm=(gf==='all'||r.dataset.group===gf); var ok=sm&&gm;
      r.style.display=ok?'':'none'; if(ok&&!first)first=r; });
    if(first)select(first.dataset.uid); }
  document.querySelectorAll('.filter-btn').forEach(function(b){ b.addEventListener('click', function(){
    document.querySelectorAll('.filter-btn').forEach(function(x){x.classList.remove('active');});
    b.classList.add('active'); sf=b.dataset.filter; apply(); }); });
  if(gs) gs.addEventListener('change', function(){ gf=gs.value; apply(); });
})();
</script>
"""


def _master_detail(items: list[dict]) -> str:
    if not items:
        return '<div class="no-failures">표시할 테스트가 없습니다.</div>'
    rows = "".join(_test_row(t, active=(i == 0)) for i, t in enumerate(items))
    cards = "\n".join(_test_card(t, active=(i == 0)) for i, t in enumerate(items))
    return (
        '<div class="master-detail"><aside class="test-list"><div class="test-list-rows">'
        f'{rows}</div></aside><main class="test-detail">{cards}</main></div>'
    )


def _filter_bar(counts: dict[str, int], groups: list[str]) -> str:
    total = sum(counts.values())
    opts = "".join(f'<option value="{html.escape(g)}">{html.escape(g)}</option>' for g in groups)
    return (
        '<div class="filter-bar">'
        f'<button class="filter-btn active" data-filter="all">전체 <span class="filter-cnt">{total}</span></button>'
        f'<button class="filter-btn" data-filter="passed">✅ 통과 <span class="filter-cnt">{counts.get("passed", 0)}</span></button>'
        f'<button class="filter-btn" data-filter="failed">❌ 실패 <span class="filter-cnt">{counts.get("failed", 0)}</span></button>'
        f'<button class="filter-btn" data-filter="broken">⚠️ 깨짐 <span class="filter-cnt">{counts.get("broken", 0)}</span></button>'
        f'<button class="filter-btn" data-filter="skipped">⏭️ 스킵 <span class="filter-cnt">{counts.get("skipped", 0)}</span></button>'
        f'<select class="group-filter" aria-label="그룹 필터"><option value="all">전체 그룹</option>{opts}</select></div>'
    )


# ============================================================ overview
def _overview_body(items, results_dir, sample):
    stats = {k: 0 for k in ("passed", "failed", "broken", "skipped", "unknown")}
    for it in items:
        stats[it["status"]] = stats.get(it["status"], 0) + 1
    total = len(items)
    denom = stats["passed"] + stats["failed"] + stats["broken"] + stats["skipped"]
    pass_rate = (stats["passed"] / denom * 100) if denom else 0.0
    starts = [it["start"] for it in items if isinstance(it["start"], int)]
    stops = [it["stop"] for it in items if isinstance(it["stop"], int)]
    wall = (max(stops) - min(starts)) if starts and stops else 0
    cpu = sum(it["duration"] for it in items)
    parallel = (cpu / wall) if wall else 1.0

    groups: dict[str, dict] = {}
    for it in items:
        g = groups.setdefault(it["feature"], {"group": it["feature"], "total": 0, "passed": 0, "failed": 0, "broken": 0, "skipped": 0})
        g["total"] += 1
        g[it["status"]] = g.get(it["status"], 0) + 1
    for g in groups.values():
        d = g["passed"] + g["failed"] + g["broken"] + g["skipped"]
        g["rate"] = (g["passed"] / d * 100) if d else 0.0
    group_rows = sorted(groups.values(), key=lambda g: g["group"])
    slowest = sorted(items, key=lambda x: -x["duration"])[:5]
    failed = sorted([it for it in items if it["status"] in ("failed", "broken", "skipped")],
                    key=lambda t: (_SEV_ORDER.get(t.get("severity"), 9), t["name"]))[:5]

    counter = "".join(
        f'<div class="hero-count hero-count-{k}"><span class="hero-count-num">{stats.get(k, 0)}</span>'
        f'<span class="hero-count-label">{lab}</span></div>'
        for k, lab in [("passed", "✅ 통과"), ("failed", "❌ 실패"), ("broken", "⚠️ 깨짐"), ("skipped", "⏭️ 스킵")])
    meta = (f'<span>런 소요 시간 <strong>{_fmt(wall)}</strong></span>'
            f'<span>총 CPU 시간 <strong>{_fmt(cpu)}</strong></span>'
            f'<span>병렬도 <strong>{parallel:.2f}x</strong></span>'
            f'<span>전체 테스트 <strong>{total}건</strong></span>')
    hero = (f'<section class="overview-hero"><div class="hero-pass-rate {_rate_class(pass_rate)}">'
            f'<span class="hero-pass-rate-value">{pass_rate:.1f}%</span>'
            f'<span class="hero-pass-rate-label">통과율</span></div>'
            f'<div class="hero-counts">{counter}</div><div class="hero-meta">{meta}</div></section>')

    if failed:
        pc = ('<section class="overview-card"><div class="overview-card__header">'
              '<h2 class="overview-card__title">🚨 우선순위 점검</h2>'
              '<a class="card-cta card-cta--inline" href="failures.html">실패 로그 전체 보기 →</a></div>'
              f'<ul class="mini-test-list">{"".join(_mini_row(t, show_severity=True) for t in failed)}</ul></section>')
    else:
        pc = ('<section class="overview-card overview-card-empty"><h2 class="overview-card__title">🚨 우선순위 점검</h2>'
              '<p class="empty-text">🎉 점검할 항목이 없습니다.</p></section>')
    sc = ('<section class="overview-card"><div class="overview-card__header">'
          '<h2 class="overview-card__title">🐢 가장 느린 테스트</h2>'
          '<a class="card-cta card-cta--inline" href="timeline.html">타임라인 보기 →</a></div>'
          f'<ul class="mini-test-list">{"".join(_mini_row(t, show_severity=False) for t in slowest)}</ul></section>')

    attention = [g for g in group_rows if g["failed"] or g["broken"] or g["skipped"]]
    passing = [g for g in group_rows if g not in attention]
    sections = []
    if attention:
        rows = []
        for g in attention:
            extras = [f"❌ {g['failed']}" if g["failed"] else "", f"⚠️ {g['broken']}" if g["broken"] else "", f"⏭️ {g['skipped']}" if g["skipped"] else ""]
            extra = f'<span class="group-extra">{" · ".join(x for x in extras if x)}</span>'
            rows.append(f'<li class="group-row"><span class="group-name">{html.escape(g["group"])}</span>'
                        f'<span class="group-count">{g["total"]}건</span>'
                        f'<div class="group-bar"><div class="group-bar-fill {_rate_class(g["rate"])}" style="width:{g["rate"]:.1f}%"></div></div>'
                        f'<span class="group-rate">{g["rate"]:.0f}%</span>{extra}</li>')
        sections.append(f'<div class="groups-attention"><h3 class="groups-subtitle">⚠️ 주의 그룹 ({len(attention)}건)</h3>'
                        f'<ul class="group-list">{"".join(rows)}</ul></div>')
    if passing:
        chips = " · ".join(f'<span class="group-chip">{html.escape(g["group"])} <em>{g["total"]}</em></span>' for g in passing)
        sections.append(f'<div class="groups-passing"><h3 class="groups-subtitle">✅ 모두 통과 ({len(passing)}개 그룹)</h3>'
                        f'<p class="groups-inline">{chips}</p></div>')
    gc = (f'<section class="overview-card overview-card-wide"><h2 class="overview-card__title">'
          f'🗂️ 점검 영역 ({len(group_rows)}개 그룹, {total}개 TC)</h2>{"".join(sections)}</section>') if group_rows else ""

    env = _read_env(results_dir)
    ex = _read_executor(results_dir)
    env_rows = "".join(f'<tr><th>{html.escape(k)}</th><td>{html.escape(v)}</td></tr>' for k, v in env.items())
    if ex.get("buildUrl"):
        env_rows += f'<tr><th>Build</th><td><a href="{html.escape(ex["buildUrl"])}" target="_blank">{html.escape(ex.get("buildName", "CI"))}</a></td></tr>'
    ec = f'<section class="overview-card"><h2 class="overview-card__title">⚙️ 실행 환경</h2><table class="env-table"><tbody>{env_rows}</tbody></table></section>'
    banner = _SAMPLE_BANNER if sample else ""
    return f'{banner}{hero}<div class="overview-grid">{pc}{sc}</div>{gc}<div class="overview-grid">{ec}</div>'


# ============================================================ failures / test-cases
def _failures_body(items, sample):
    bad = sorted([it for it in items if it["status"] in ("failed", "broken", "skipped")],
                 key=lambda t: ({"failed": 0, "broken": 1, "skipped": 2}.get(t["status"], 9), _SEV_ORDER.get(t.get("severity"), 9)))
    if not bad:
        return '<div class="no-failures">🎉 실패하거나 스킵된 테스트가 없습니다.</div>'
    banner = _SAMPLE_BANNER if sample else ""
    return f'{banner}{_master_detail(bad)}'


def _testcases_body(items, sample):
    if not items:
        return '<div class="no-failures">아직 실행된 테스트가 없습니다.</div>'
    counts: dict[str, int] = {}
    for it in items:
        counts[it["status"]] = counts.get(it["status"], 0) + 1
    groups = sorted({it["feature"] for it in items})
    banner = _SAMPLE_BANNER if sample else ""
    ordered = sorted(items, key=lambda t: ({"failed": 0, "broken": 1, "skipped": 2, "passed": 3}.get(t["status"], 9), t["name"]))
    return f'{banner}{_filter_bar(counts, groups)}{_master_detail(ordered)}'


# ============================================================ timeline
def _timeline_body(items, sample):
    timed = [it for it in items if isinstance(it["start"], int) and isinstance(it["stop"], int)]
    if not timed:
        return '<div class="no-failures">📭 타임라인 데이터가 없습니다.</div>'
    min_start = min(it["start"] for it in timed)
    span = max(max(it["stop"] for it in timed) - min_start, 1)
    lanes: dict[str, list[dict]] = {}
    for it in timed:
        lanes.setdefault(it["thread"], []).append(it)
    rows = []
    for lane in sorted(lanes):
        bars = []
        for it in lanes[lane]:
            left = (it["start"] - min_start) / span * 100
            width = max(it["duration"] / span * 100, 0.4)
            _id, label = _split_id(it["name"])
            bars.append(f'<div class="tl-bar tl-bar-{it["status"]}" style="left:{left:.2f}%;width:{width:.2f}%" '
                        f'title="{html.escape((_id or label) + " — " + _fmt(it["duration"]))}">'
                        f'<span class="tl-bar-label">{html.escape(_id or label)}</span></div>')
        rows.append(f'<div class="tl-row"><div class="tl-row-label">{html.escape(lane)}</div>'
                    f'<div class="tl-row-track">{"".join(bars)}</div></div>')
    cpu = sum(it["duration"] for it in timed)
    stats = (f'<div class="tl-stats"><span><strong>{len(timed)}</strong>건</span>'
             f'<span>런 소요 시간 <strong>{_fmt(span)}</strong></span>'
             f'<span>총 CPU 시간 <strong>{_fmt(cpu)}</strong></span>'
             f'<span>병렬도 <strong>{cpu / span:.2f}x</strong></span><span>워커 <strong>{len(lanes)}</strong></span></div>')
    legend = ('<div class="tl-legend">'
              '<span class="tl-legend-item"><span class="tl-legend-swatch tl-bar-passed"></span>통과</span>'
              '<span class="tl-legend-item"><span class="tl-legend-swatch tl-bar-failed"></span>실패</span>'
              '<span class="tl-legend-item"><span class="tl-legend-swatch tl-bar-broken"></span>깨짐</span>'
              '<span class="tl-legend-item"><span class="tl-legend-swatch tl-bar-skipped"></span>스킵</span></div>')
    banner = _SAMPLE_BANNER if sample else ""
    return f'{banner}{stats}<section class="tl-chart"><div class="tl-rows">{"".join(rows)}</div></section>{legend}'


# ============================================================ trends (AI 진단 정확도 + 차트)
_VW, _VH, _PL, _PR, _PT, _PB = 360, 100, 36, 8, 8, 22


def _load_flaky(results_dir: str) -> list[dict]:
    for path in glob.glob(str(Path(results_dir) / "flaky_history_*.json")):
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except (OSError, json.JSONDecodeError):
            continue
    return []


def _load_accuracy(results_dir: str) -> dict | None:
    path = Path(results_dir) / "diagnose" / "_accuracy.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
    return None


def _line_chart(values: list[float], *, accuracy: bool = False) -> str:
    if len(values) < 2:
        return '<div class="trends-empty">데이터 누적 후 표시</div>'
    cw, ch = _VW - _PL - _PR, _VH - _PT - _PB
    base_y = _PT + ch
    n = len(values)
    vmax = max(values) or 1
    if accuracy:
        vmax = 1.0
    pts = [(_PL + (i / (n - 1)) * cw, _PT + (1 - (v / vmax)) * ch) for i, v in enumerate(values)]
    path = " L ".join(f"{x:.1f} {y:.1f}" for x, y in pts)
    area = f"M {pts[0][0]:.1f} {base_y:.1f} L {path} L {pts[-1][0]:.1f} {base_y:.1f} Z"
    cls = "--accuracy" if accuracy else ""
    grid = []
    labels = (("100%", 1.0), ("50%", 0.5), ("0%", 0.0)) if accuracy else ((str(int(vmax)), 1.0), (str(int(vmax // 2)), 0.5), ("0", 0.0))
    for txt, ratio in labels:
        y = _PT + (1 - ratio) * ch
        grid.append(f'<line x1="{_PL}" y1="{y:.1f}" x2="{_VW - _PR}" y2="{y:.1f}" class="chart-grid"/>'
                    f'<text x="{_PL - 6}" y="{y + 3:.1f}" class="chart-axis-label" text-anchor="end">{txt}</text>')
    dots = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.5" class="chart-point chart-point{cls}"/>' for x, y in pts)
    return (f'<svg class="trends-chart trends-chart{cls}" viewBox="0 0 {_VW} {_VH}" preserveAspectRatio="xMidYMid meet">'
            f'{"".join(grid)}<path d="{area}" class="chart-area chart-area{cls}"/>'
            f'<path d="M {path}" class="chart-line chart-line{cls}"/>{dots}</svg>')


def _accuracy_card(summary: dict | None) -> str:
    if not summary:
        return ('<section class="trends-accuracy"><div class="trends-card"><h3>🧠 AI 진단 정확도</h3>'
                '<div class="trends-empty">누적 데이터 없음</div></div></section>')
    coarse = summary.get("match_coarse_rate", 0) or 0
    fine = summary.get("match_fine_rate", 0) or 0
    helpful = summary.get("action_helpful_rate", 0) or 0

    def cls(r):
        return "rate-low" if r >= 0.7 else "rate-high" if r >= 0.5 else "rate-always"
    spark = _line_chart([(r.get("fine_correct", 0) / r["recorded"]) for r in summary.get("per_run", []) if r.get("recorded")], accuracy=True)
    conf = list((summary.get("confusion_fine") or {}).items())[:3]
    conf_html = ("".join(f'<li><code>{html.escape(p)}</code><span class="rate-low">{c}</span></li>' for p, c in conf)
                 if conf else '<li><span class="trends-empty">잘못 분류 없음 ✨</span></li>')
    meta = (f'{summary.get("total_predictions", 0)}건 중 {summary.get("total_recorded", 0)}건 기록 · '
            f'누락 {summary.get("unrecorded_rate", 0):.0%} · 마지막 집계 {html.escape(summary.get("generated_at", "")[:16].replace("T", " "))}')
    return (
        '<section class="trends-accuracy"><div class="trends-row trends-row--accuracy">'
        '<div class="trends-card"><h3>🧠 AI 진단 정확도</h3><div class="accuracy-kpis">'
        f'<div class="accuracy-kpi"><div class="accuracy-kpi__label">대분류 적중률</div><div class="accuracy-kpi__value {cls(coarse)}">{coarse:.0%}</div></div>'
        f'<div class="accuracy-kpi"><div class="accuracy-kpi__label">세부 분류 적중률</div><div class="accuracy-kpi__value {cls(fine)}">{fine:.0%}</div></div>'
        f'<div class="accuracy-kpi"><div class="accuracy-kpi__label">권장 조치 적중률</div><div class="accuracy-kpi__value">{helpful:.0%}</div></div>'
        f'</div><div class="accuracy-meta">{meta}</div></div>'
        f'<div class="trends-card"><h3>세부 분류 적중률 추이</h3>{spark}</div></div>'
        f'<div class="trends-card"><h3>잘못 분류 Top 3 (예측 → 실제)</h3><ul class="trends-candidates">{conf_html}</ul></div></section>'
    )


def _trends_body(items, results_dir, sample):
    flaky = _load_flaky(results_dir)
    accuracy = _load_accuracy(results_dir)
    window = min(10, len(flaky))
    recent = flaky[-window:] if flaky else []
    # fail 추세 차트
    fail_counts = [len(e.get("failures", [])) for e in recent]
    chart = _line_chart([float(c) for c in fail_counts]) if len(fail_counts) >= 2 else '<div class="trends-empty">데이터 없음</div>'
    # fail 빈도 top
    counter: Counter[str] = Counter()
    for e in recent:
        for t in e.get("failures", []):
            counter[t] += 1
    total_runs = len(recent) or 1
    top_rows = []
    for test, cnt in counter.most_common(10):
        rate = cnt / total_runs
        rc = "rate-always" if cnt == total_runs else ("rate-high" if rate >= 0.4 else "rate-low")
        dots = "".join('<span class="timeline-dot timeline-dot--fail"></span>' if test in (e.get("failures") or [])
                       else '<span class="timeline-dot timeline-dot--pass"></span>' for e in recent)
        top_rows.append(f'<tr><td><span class="{rc}">{rate:.0%} ({cnt}/{total_runs})</span></td>'
                        f'<td><code>{html.escape(test)}</code></td><td><span class="trends-timeline">{dots}</span></td></tr>')
    top_table = (f'<table class="trends-table trends-table--fails"><thead><tr><th>fail rate</th><th>테스트</th><th>추이</th></tr></thead>'
                 f'<tbody>{"".join(top_rows)}</tbody></table>') if top_rows else '<div class="trends-empty">최근 fail 없음 ✨</div>'
    # quarantine 후보
    cand = sorted([(t, c, c / total_runs) for t, c in counter.items() if c / total_runs >= 0.4 and c < total_runs], key=lambda x: -x[2])
    if cand:
        items_html = "".join(f'<li><code>{html.escape(t)}</code><span class="rate-high">{r:.0%} ({c}/{total_runs})</span></li>' for t, c, r in cand)
        quarantine = (f'<ul class="trends-candidates">{items_html}</ul>'
                      '<p class="trends-hint">⚠️ 안정 결과를 가리는 노이즈 — 자동화 측 원인 점검이 필요한 후보. 원인 분석 후 격리 마커 적용 권장.</p>')
    else:
        quarantine = f'<div class="trends-empty">최근 {total_runs}회 중 {math.ceil(0.4 * total_runs)}회↑ 깨진 테스트 없음 (안정)</div>'
    banner = _SAMPLE_BANNER if sample else ""
    return (
        f'{banner}{_accuracy_card(accuracy)}'
        f'<section class="trends-env trends-env--active"><h2>QA</h2>'
        f'<div class="trends-env-meta">누적 {len(flaky)} runs (Sample)</div>'
        f'<div class="trends-row"><div class="trends-card"><h3>최근 {window} 런 fail 추세</h3>{chart}</div>'
        f'<div class="trends-card"><h3>자주 깨지는 테스트 (격리 검토 후보)</h3>{quarantine}</div></div>'
        f'<div class="trends-card"><h3>Fail 빈도 Top 10 (최근 {window} 런)</h3>{top_table}</div></section>'
    )


_TRENDS_STYLE = """
<style>
  .trends-card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 20px; margin-bottom: 16px; box-shadow: 0 1px 2px rgba(45,36,64,.03); }
  .trends-card h3 { margin: 0 0 14px; font-size: 16px; font-weight: 700; color: var(--text); }
  .trends-row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  .trends-env h2 { margin: 0 0 6px; font-size: 22px; font-weight: 800; color: var(--primary); }
  .trends-env-meta { color: var(--muted); font-size: 13px; margin-bottom: 16px; }
  .trends-chart { width: 100%; height: auto; display: block; overflow: visible; }
  .chart-grid { stroke: #F0EDF5; stroke-width: 1; stroke-dasharray: 3 3; }
  .chart-area { fill: var(--failed-text); fill-opacity: .12; }
  .chart-line { fill: none; stroke: var(--failed-text); stroke-width: 2; stroke-linecap: round; }
  .chart-point { fill: var(--surface); stroke: var(--failed-text); stroke-width: 2; }
  .chart-line--accuracy { stroke: var(--primary); } .chart-area--accuracy { fill: var(--primary); fill-opacity: .10; } .chart-point--accuracy { stroke: var(--primary); }
  .chart-axis-label { fill: var(--muted); font-size: 10px; font-family: 'JetBrains Mono', monospace; }
  .trends-table { width: 100%; border-collapse: collapse; font-size: 14px; }
  .trends-table thead th { text-align: left; color: var(--muted); font-weight: 600; font-size: 12px; padding: 8px 10px; border-bottom: 1px solid var(--border); text-transform: uppercase; }
  .trends-table tbody td { padding: 10px; border-bottom: 1px solid #F0EDF5; vertical-align: middle; }
  .trends-table code { font-size: 13px; background: var(--bg); padding: 2px 6px; border-radius: 4px; }
  .trends-timeline { display: inline-flex; gap: 3px; }
  .timeline-dot { width: 9px; height: 9px; border-radius: 50%; display: inline-block; }
  .timeline-dot--fail { background: var(--failed-text); } .timeline-dot--pass { background: transparent; border: 1px solid #D8D4DF; }
  .rate-high, .rate-always, .rate-low { display: inline-block; font-weight: 600; font-size: 12px; padding: 3px 10px; border-radius: 999px; font-variant-numeric: tabular-nums; }
  .rate-high { color: var(--failed-text); background: var(--failed-bg); } .rate-always { color: #8B0000; background: #FFE0E0; } .rate-low { color: var(--muted); background: var(--bg); }
  .trends-candidates { list-style: none; padding: 0; margin: 0; display: grid; gap: 6px; }
  .trends-candidates li { display: flex; justify-content: space-between; align-items: center; gap: 12px; padding: 8px 12px; background: var(--bg); border-radius: 8px; font-size: 14px; }
  .trends-candidates code { background: transparent; padding: 0; }
  .trends-hint { font-size: 13px; color: var(--muted); margin: 12px 0 0; padding-top: 12px; border-top: 1px solid #F0EDF5; }
  .trends-empty { color: var(--muted); font-size: 14px; padding: 24px 12px; text-align: center; background: var(--bg); border-radius: 8px; }
  .trends-accuracy { margin-bottom: 24px; }
  .accuracy-kpis { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 14px; }
  .accuracy-kpi { background: var(--bg); border-radius: 10px; padding: 14px 12px; text-align: center; }
  .accuracy-kpi__label { font-size: 12px; color: var(--muted); font-weight: 600; text-transform: uppercase; margin-bottom: 6px; }
  .accuracy-kpi__value { font-size: 26px; font-weight: 800; color: var(--text); font-variant-numeric: tabular-nums; }
  .accuracy-kpi__value.rate-low, .accuracy-kpi__value.rate-high, .accuracy-kpi__value.rate-always { display: inline-block; padding: 4px 14px; font-size: 22px; }
  .accuracy-meta { font-size: 13px; color: var(--muted); border-top: 1px solid #F0EDF5; padding-top: 12px; }
  @media (max-width: 900px) { .trends-row { grid-template-columns: 1fr; } .accuracy-kpis { grid-template-columns: 1fr; } }
</style>
"""


def generate_all(results_dir: str, report_dir: str, *, sample: bool = True) -> None:
    items = _load(results_dir)
    out = Path(report_dir)
    out.mkdir(parents=True, exist_ok=True)
    pages = {
        "overview.html": _page("요약", "한 화면으로 보는 이번 런 결과", _overview_body(items, results_dir, sample), "overview"),
        "failures.html": _page("실패 로그", "실패·깨짐·스킵 테스트", _failures_body(items, sample), "failures", body_extra=_INTERACTION_JS),
        "trends.html": _page("추이", "AI 진단 정확도 · fail 추세 · 격리 후보", _trends_body(items, results_dir, sample), "trends", head_extra=_TRENDS_STYLE),
        "timeline.html": _page("타임라인", "워커별 실행 시간선", _timeline_body(items, sample), "timeline"),
        "test-cases.html": _page("테스트 케이스", "전체 테스트 — 상태·그룹별 필터로 좁혀 보기", _testcases_body(items, sample), "tests", body_extra=_INTERACTION_JS),
    }
    for name, content in pages.items():
        (out / name).write_text(content, encoding="utf-8")


def generate(results_dir: str, report_dir: str) -> Path:
    generate_all(results_dir, report_dir)
    return Path(report_dir) / "overview.html"


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: python scripts/generate_report.py <allure-results-dir> <report-dir>")
        return 1
    generate_all(sys.argv[1], sys.argv[2])
    print(f"[generate_report] 멀티 페이지 생성: {sys.argv[2]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
