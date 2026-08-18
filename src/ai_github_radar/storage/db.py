"""DB session 管理 — T014.

提供 session_scope 上下文管理器 + engine / session_factory 单例。
"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from ai_github_radar.db import Base

_engine: Optional[Engine] = None
_factory: Optional[sessionmaker] = None


def _coerce_db_url(url: str) -> str:
    """sqlite 相对路径转绝对(锚定 cwd),避免 cron/cwd 变化。"""
    if not url.startswith("sqlite:///"):
        return url
    rel = url[len("sqlite:///"):]
    if rel.startswith("/"):
        return url  # 绝对
    p = Path(rel)
    if not p.is_absolute():
        p = (Path.cwd() / p).resolve()
        return f"sqlite:///{p}"
    return url


def get_engine(db_url: str = "sqlite:///./data/radar.db") -> Engine:
    """获取(或创建)Engine 单例。"""
    global _engine
    if _engine is None:
        from sqlalchemy import create_engine
        url = _coerce_db_url(db_url)
        # sqlite 文件需要父目录
        if url.startswith("sqlite:///"):
            rel = url[len("sqlite:///"):]
            if rel and rel != ":memory:":
                p = Path(rel)
                p.parent.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(url, future=True)
    return _engine


def get_session_factory(db_url: str = "sqlite:///./data/radar.db") -> sessionmaker:
    """获取(或创建)sessionmaker。"""
    global _factory
    if _factory is None:
        _factory = sessionmaker(bind=get_engine(db_url), expire_on_commit=False)
    return _factory


def init_db(db_url: str = "sqlite:///./data/radar.db") -> None:
    """create_all tables。"""
    Base.metadata.create_all(get_engine(db_url))


def reset_for_testing() -> None:
    """重置单例(测试用)。"""
    global _engine, _factory
    _engine = None
    _factory = None


@contextmanager
def session_scope(db_url: str = "sqlite:///./data/radar.db") -> Iterator[Session]:
    """事务上下文:commit on success, rollback on error。"""
    factory = get_session_factory(db_url)
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()