"""환경 설정 로더 — config/base.yml 을 읽어 dict 로 반환.

URL·타임아웃 같은 값을 코드에 하드코딩하지 않고 설정 파일에서 주입하기 위한 모듈.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

# src/utils/config.py → src/ → src/config/base.yml
CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "base.yml"


@lru_cache(maxsize=1)
def load_config() -> dict:
    """base.yml 을 읽어 설정 dict 반환. (세션 내 캐시)"""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"설정 파일을 찾을 수 없습니다: {CONFIG_PATH}")
    with CONFIG_PATH.open(encoding="utf-8") as config_file:
        return yaml.safe_load(config_file)
