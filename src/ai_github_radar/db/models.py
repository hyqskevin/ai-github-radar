"""ORM 模型定义 — T003.

4 张表(stars / keywords / trending_snapshots / recommendations),
字段按 docs/database-design.md DDL 一一对应。
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ai_github_radar.db import Base


def _utcnow_iso() -> str:
    """ISO 8601 UTC 时间字符串,默认字段填充。"""
    return datetime.utcnow().isoformat(timespec="seconds")


class Star(Base):
    """已 star 仓库快照。init 时全量刷新。

    字段映射 docs/database-design.md §stars。
    """

    __tablename__ = "stars"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    repo_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    owner: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    language: Mapped[Optional[str]] = mapped_column(Text, nullable=True, index=True)
    topics: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array str
    homepage: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    stargazers_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    pushed_at: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    starred_at: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    fetched_at: Mapped[str] = mapped_column(
        Text, nullable=False, default=_utcnow_iso, index=True
    )
    archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class Keyword(Base):
    """关键字订阅表。TF-IDF 自动提的或用户手加。"""

    __tablename__ = "keywords"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    term: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="manual")  # "auto" | "manual"
    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, index=True
    )
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=_utcnow_iso)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False, default=_utcnow_iso)


class TrendingSnapshot(Base):
    """trending 每日快照。"""

    __tablename__ = "trending_snapshots"
    __table_args__ = (
        UniqueConstraint("repo_id", "snapshot_date", name="uq_trending_repo_date"),
        Index("idx_trending_date", "snapshot_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    repo_id: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot_date: Mapped[str] = mapped_column(Text, nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    stars_today: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    language: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    fetched_at: Mapped[str] = mapped_column(Text, nullable=False, default=_utcnow_iso)


class Recommendation(Base):
    """已推送的推荐记录。"""

    __tablename__ = "recommendations"
    __table_args__ = (
        UniqueConstraint("repo_id", "pushed_at", name="uq_rec_repo_pushed"),
        Index("idx_rec_pushed", "pushed_at"),
        Index("idx_rec_repo", "repo_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    repo_id: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    matched_keywords: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    channel: Mapped[str] = mapped_column(String(16), nullable=False)
    pushed_at: Mapped[str] = mapped_column(Text, nullable=False)