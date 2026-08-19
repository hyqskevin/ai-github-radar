"""DB Repository 集合 — T014.

StarRepository / TrendingSnapshotRepository / RecommendationRepository + KeywordRepository(re-export)。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ai_github_radar.db.models import (
    Keyword,
    Recommendation,
    Star,
    TrendingSnapshot,
)
from ai_github_radar.keywords.repository import KeywordRepository


class StarRepository:
    def __init__(self, session: Session):
        self._s = session

    def upsert_many(self, stars: list[dict]) -> int:
        """按 repo_id upsert。stars: [{repo_id, owner, name, full_name, ...}]"""
        count = 0
        for s in stars:
            existing = self._s.get(Star, s["repo_id"]) if self._s.get(Star, s["repo_id"]) is not None else None
            # 简化:用 select + insert/update
            stmt = select(Star).where(Star.repo_id == s["repo_id"])
            existing = self._s.execute(stmt).scalar_one_or_none()
            now = datetime.utcnow().isoformat()
            if existing is None:
                self._s.add(Star(
                    repo_id=s["repo_id"],
                    owner=s.get("owner", ""),
                    name=s.get("name", ""),
                    full_name=s.get("full_name", ""),
                    description=s.get("description"),
                    language=s.get("language"),
                    topics=s.get("topics"),
                    homepage=s.get("homepage"),
                    stargazers_count=s.get("stargazers_count"),
                    pushed_at=s.get("pushed_at"),
                    starred_at=s.get("starred_at"),
                    fetched_at=s.get("fetched_at", now),
                    archived=s.get("archived", False),
                ))
            else:
                for k in ("owner", "name", "full_name", "description",
                          "language", "topics", "homepage", "stargazers_count",
                          "pushed_at", "starred_at", "archived"):
                    setattr(existing, k, s.get(k, getattr(existing, k)))
                existing.fetched_at = s.get("fetched_at", now)
            count += 1
        self._s.flush()
        return count

    def list_all(self) -> list[Star]:
        return list(self._s.execute(select(Star)).scalars())

    def list_missing_summary(self, limit: int = 100) -> list[Star]:
        """返还没生成 summary 的 stars(summary is null)。"""
        stmt = (
            select(Star)
            .where(Star.summary.is_(None))
            .order_by(Star.fetched_at.desc())
            .limit(limit)
        )
        return list(self._s.execute(stmt).scalars())

    def all_descriptions(self, limit: int = 30) -> list[str]:
        """返回最多 N 条 star 的 description(用于 LLM 关键字 rationale 上下文)。"""
        stmt = (
            select(Star.description)
            .where(Star.description.isnot(None))
            .limit(limit)
        )
        return [row[0] for row in self._s.execute(stmt).all()]

    def count_all(self) -> int:
        """总 star 数(给 LLM 上下文用)。"""
        from sqlalchemy import func
        stmt = select(func.count()).select_from(Star)
        return int(self._s.execute(stmt).scalar_one())


class TrendingSnapshotRepository:
    def __init__(self, session: Session):
        self._s = session

    def upsert_many(self, snapshots: list[dict]) -> int:
        """snapshots: [{repo_id, snapshot_date, rank, stars_today, language, description}]"""
        count = 0
        for s in snapshots:
            now = datetime.utcnow().isoformat()
            self._s.add(TrendingSnapshot(
                repo_id=s["repo_id"],
                snapshot_date=s["snapshot_date"],
                rank=s["rank"],
                stars_today=s.get("stars_today"),
                language=s.get("language"),
                description=s.get("description"),
                fetched_at=s.get("fetched_at", now),
            ))
            count += 1
        self._s.flush()
        return count

    def list_by_date(self, snapshot_date: str) -> list[TrendingSnapshot]:
        stmt = select(TrendingSnapshot).where(
            TrendingSnapshot.snapshot_date == snapshot_date
        ).order_by(TrendingSnapshot.rank)
        return list(self._s.execute(stmt).scalars())


class RecommendationRepository:
    def __init__(self, session: Session):
        self._s = session

    def record_push(
        self,
        repo_id: int,
        score: float,
        matched_keywords: list[str],
        channel: str,
        pushed_at: Optional[str] = None,
    ) -> Recommendation:
        """记录一次推送(写 Recommendation 行)。"""
        now = pushed_at or datetime.utcnow().isoformat()
        rec = Recommendation(
            repo_id=repo_id,
            score=score,
            matched_keywords=",".join(matched_keywords),
            channel=channel,
            pushed_at=now,
        )
        self._s.add(rec)
        self._s.flush()
        return rec

    def recent_repo_ids(self, days: int = 7) -> set[int]:
        """N-day dedupe 集合。"""
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        stmt = (
            select(Recommendation.repo_id)
            .where(Recommendation.pushed_at >= cutoff)
            .distinct()
        )
        return {row[0] for row in self._s.execute(stmt).all()}


__all__ = [
    "KeywordRepository",
    "RecommendationRepository",
    "StarRepository",
    "TrendingSnapshotRepository",
]