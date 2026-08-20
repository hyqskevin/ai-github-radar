"""services/settings.py — Settings 表的 CRUD (T125).

设计:key-value 存储,用 sqlalchemy JSON 序列化。
- get(key, default): 读
- set(key, value): 写
- all(): 返所有
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from ai_github_radar.db.models import Setting


def _utcnow() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")


def get_setting(s: Session, key: str, default: Optional[str] = None) -> Optional[str]:
    row = s.get(Setting, key)
    return row.value if row else default


def get_setting_json(s: Session, key: str, default: Optional[Any] = None) -> Any:
    raw = get_setting(s, key)
    if raw is None:
        return default
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return default


def set_setting(s: Session, key: str, value: Any) -> Setting:
    """value 自动 JSON 序列化(非 str)或原样存(str)。"""
    if isinstance(value, str):
        encoded = value
    else:
        encoded = json.dumps(value, ensure_ascii=False)
    existing = s.get(Setting, key)
    if existing:
        existing.value = encoded
        existing.updated_at = _utcnow()
        return existing
    new = Setting(key=key, value=encoded, updated_at=_utcnow())
    s.add(new)
    return new


def list_settings(s: Session) -> dict[str, str]:
    return {r.key: r.value for r in s.query(Setting).all()}


# ---------------------------------------------------------------------------
# 已知设置 keys 常量(集中管理避免拼错)
# ---------------------------------------------------------------------------

KEY_LLM_PROVIDER = "llm.provider"
KEY_LLM_MODEL = "llm.model"
KEY_LLM_API_KEY = "llm.api_key"
KEY_LLM_BASE_URL = "llm.base_url"  # T142: 自定义 OpenAI 兼容 API 端点
KEY_GITHUB_USER = "github.user"
KEY_GITHUB_TOKEN = "github.token"
KEY_SCAN_INTERVAL_CRON = "scan.cron"  # cron 表达式
KEY_PUSH_TARGET = "push.target"