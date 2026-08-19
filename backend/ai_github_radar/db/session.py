"""session.py — engine 工厂 + Session 上下文 + init_db helper.

路径解析顺序:
  1. get_engine(db_path=...) 显式参数
  2. RADAR_DB_PATH 环境变量
  3. load_settings().db_url(SQLite URL 解析成文件路径)
  4. 默认 ./data/radar.db

contextmanager session_scope(factory) 提供 commit / rollback / close 自动管理。
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional
from urllib.parse import urlparse

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from ai_github_radar.db import Base


def _resolve_db_path(db_path: Optional[str]) -> str:
    """路径解析。返回最终 SQLite 文件路径。"""
    if db_path:
        return db_path
    env_path = os.environ.get("RADAR_DB_PATH")
    if env_path:
        return env_path
    try:
        from ai_github_radar.config import load_settings

        load_settings.cache_clear()
        settings = load_settings()
        url = str(settings.db_url)
        # sqlite:///./data/radar.db → ./data/radar.db
        if url.startswith("sqlite:"):
            parsed = urlparse(url)
            netloc = parsed.netloc  # 空 或 "user:pass@host"
            path = parsed.path
            # sqlite:////abs/path.db (4 slashes → absolute)
            if netloc and not path.startswith("/"):
                return netloc + path
            return path.lstrip("/")
    except Exception:
        # config 加载失败(无 .env 等),回退默认
        pass
    return "./data/radar.db"


def get_engine(db_path: Optional[str] = None) -> Engine:
    """构造 SQLAlchemy engine。

    SQLite 单文件模式,echo=False,无连接池(SQLite 默认 NullPool 足够)。
    """
    path = _resolve_db_path(db_path)
    url = f"sqlite:///{path}"
    # SQLite 需要 check_same_thread=False 才能在多线程用(daemon 模式会用到)
    return create_engine(
        url,
        echo=False,
        future=True,
        connect_args={"check_same_thread": False},
    )


def get_session_factory(engine: Engine) -> sessionmaker[Session]:
    """构造 sessionmaker(bind 到 engine,autoflush=False 留给调用方显式 flush)。"""
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@contextmanager
def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    """with 块自动管理 commit / rollback / close。

    成功退出 → commit;异常 → rollback + 透传。
    """
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db(engine: Engine) -> None:
    """Base.metadata.create_all(engine) — 建全部表 + 索引,幂等。"""
    # 确保父目录存在
    if engine.url.database and engine.url.database != ":memory:":
        Path(engine.url.database).parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(engine)