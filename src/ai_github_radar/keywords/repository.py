"""KeywordRepository — T006 Keyword ORM CRUD.

所有写操作在调用方传入的 session_scope 内执行(本类不创建 session),
session 生命周期由 db.session_scope 管理。
"""

from __future__ import annotations

from datetime import datetime
from typing import Iterable, Optional, Union

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ai_github_radar.db.models import Keyword


class KeywordRepository:
    def __init__(self, session: Session):
        self._s = session

    # ---- read ----

    def list(self, *, enabled_only: bool = False) -> list[Keyword]:
        stmt = select(Keyword)
        if enabled_only:
            stmt = stmt.where(Keyword.enabled.is_(True))
        stmt = stmt.order_by(Keyword.weight.desc(), Keyword.term.asc())
        return list(self._s.execute(stmt).scalars())

    def get_by_term(self, term: str) -> Optional[Keyword]:
        stmt = select(Keyword).where(Keyword.term == term)
        return self._s.execute(stmt).scalar_one_or_none()

    def get_by_id(self, kw_id: int) -> Optional[Keyword]:
        return self._s.get(Keyword, kw_id)

    # ---- write ----

    def upsert(
        self, term: str, weight: float = 1.0, source: str = "manual"
    ) -> Keyword:
        existing = self.get_by_term(term)
        now = datetime.utcnow().isoformat()
        if existing is not None:
            existing.weight = weight
            existing.source = source
            existing.updated_at = now
            self._s.flush()
            return existing
        kw = Keyword(
            term=term,
            weight=weight,
            source=source,
            enabled=True,
            created_at=now,
            updated_at=now,
        )
        self._s.add(kw)
        self._s.flush()
        return kw

    def add(self, term: str, weight: float = 1.0, source: str = "manual") -> Keyword:
        now = datetime.utcnow().isoformat()
        kw = Keyword(
            term=term,
            weight=weight,
            source=source,
            enabled=True,
            created_at=now,
            updated_at=now,
        )
        self._s.add(kw)
        self._s.flush()  # flush 而非 commit,让调用方控 commit
        return kw

    def delete(self, term_or_id: Union[str, int]) -> bool:
        kw: Optional[Keyword] = None
        if isinstance(term_or_id, int):
            kw = self.get_by_id(term_or_id)
        else:
            kw = self.get_by_term(term_or_id)
        if kw is None:
            return False
        self._s.delete(kw)
        self._s.flush()
        return True

    def toggle(self, term_or_id: Union[str, int]) -> Optional[Keyword]:
        kw: Optional[Keyword] = None
        if isinstance(term_or_id, int):
            kw = self.get_by_id(term_or_id)
        else:
            kw = self.get_by_term(term_or_id)
        if kw is None:
            return None
        kw.enabled = not kw.enabled
        kw.updated_at = datetime.utcnow().isoformat()
        self._s.flush()
        return kw

    # ---- 批量 ----

    def bulk_upsert_from_tfidf(
        self,
        tfidf_results: Iterable[tuple[str, float]],
        *,
        source: str = "auto",
    ) -> int:
        """把 TF-IDF 结果 upsert 到 DB,返回 upsert 数量。

        weight 归一化到 1.0-10.0(weight * 10,封顶 10)。
        """
        count = 0
        for term, raw_w in tfidf_results:
            w = max(1.0, min(raw_w * 10.0, 10.0))
            try:
                self.upsert(term, weight=w, source=source)
            except IntegrityError:
                # 极少见(并发 upsert),跳过
                self._s.rollback()
                continue
            count += 1
        return count