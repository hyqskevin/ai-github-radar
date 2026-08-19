"""db 子包 — SQLAlchemy ORM + session 管理(T003).

阶段一用 SQLite 单文件 + Base.metadata.create_all()(无 Alembic 迁移),
见 docs/database-design.md + docs/superpowers/specs/2026-08-18-db-design.md。

用法:
    from ai_github_radar.db import get_engine, init_db, session_scope
    from ai_github_radar.db.models import Keyword

    engine = get_engine()                # 默认 ./data/radar.db
    init_db(engine)                       # 建 4 张表 + 索引
    factory = get_session_factory(engine)
    with session_scope(factory) as s:
        s.add(Keyword(term="agent", ...))
"""

from __future__ import annotations

from sqlalchemy import Engine
from sqlalchemy.orm import DeclarativeBase, Session as _Session


class Base(DeclarativeBase):
    """所有 ORM Model 的共同基类。"""


from ai_github_radar.db.models import (  # noqa: E402,F401  (import 顺序:Base 必须先定义)
    Keyword,
    Recommendation,
    Star,
    TrendingSnapshot,
)
from ai_github_radar.db.session import (  # noqa: E402,F401
    get_engine,
    get_session_factory,
    init_db,
    session_scope,
)

__all__ = [
    "Base",
    "Keyword",
    "Recommendation",
    "Session",
    "Star",
    "TrendingSnapshot",
    "get_engine",
    "get_session_factory",
    "init_db",
    "session_scope",
]

# 别名,便于 `from ai_github_radar.db import Session`
Session = _Session
"""SQLAlchemy Session 类型别名(供 typing)。"""