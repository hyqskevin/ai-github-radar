"""ORM 模型定义 — T003 + T125.

7 张表(stars / keywords / trending_snapshots / recommendations /
settings / jobs / schedules),字段按 docs/database-design.md DDL 一一对应。

阶段二新增:
- settings: key-value 配置(LLM provider / API key / cron interval)
- jobs: 任务执行记录(任务监控)
- schedules: 定时任务表(cron)
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
    # T130: LLM 生成的简介(中文 1-3 句),null 表示未生成
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    summary_at: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    summary_model: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)


class Keyword(Base):
    """关键字。

    - term: 唯一
    - weight: 默认 1.0
    - source: auto (LLM 提取) / manual (用户加)
    - enabled: 启/停
    """

    __tablename__ = "keywords"
    __table_args__ = (
        UniqueConstraint("term", name="uq_keyword_term"),
        Index("idx_keyword_enabled", "enabled"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    term: Mapped[str] = mapped_column(Text, nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="manual")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # T130: LLM 为何提取这个关键字的理由(中文短句),null 表示未生成
    rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(
        Text, nullable=False, default=_utcnow_iso
    )
    updated_at: Mapped[str] = mapped_column(
        Text, nullable=False, default=_utcnow_iso, onupdate=_utcnow_iso
    )


class TrendingSnapshot(Base):
    """每日 trending 快照。

    - fetched_at: 拉取时间
    - repos: JSON list,TrendingRepo dict 序列化
    """

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


class Setting(Base):
    """应用设置表(key-value)。

    阶段二:LLM provider / API key / scan interval / push target 等。
    """

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False, default=_utcnow_iso)


class Job(Base):
    """任务执行记录(任务监控)。

    字段:
    - name: scan / init / 任何内部任务
    - status: pending / running / success / failed
    - started_at / finished_at / duration_ms
    - payload: JSON,任务输入参数
    - result: JSON,任务结果摘要
    - error: 错误堆栈
    """

    __tablename__ = "jobs"
    __table_args__ = (Index("idx_job_started", "started_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    started_at: Mapped[str] = mapped_column(Text, nullable=False, default=_utcnow_iso)
    finished_at: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    payload: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class Schedule(Base):
    """定时任务配置。

    - name: scan_keywords / refresh_stars / 等
    - cron: 标准 5 段 cron 表达式
    - enabled: True/False
    - last_run_at: 上次跑的时间
    - next_run_at: 估算下次时间
    """

    __tablename__ = "schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    cron: Mapped[str] = mapped_column(String(64), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    payload: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_run_at: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    next_run_at: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=_utcnow_iso)