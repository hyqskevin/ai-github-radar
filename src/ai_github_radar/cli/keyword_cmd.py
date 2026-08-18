"""radar keyword 子命令组。"""

from __future__ import annotations

import click

from ai_github_radar.storage.db import init_db, session_scope
from ai_github_radar.storage.repositories import KeywordRepository

__all__ = ["keyword_cmd"]


@click.group("keyword")
def keyword_cmd() -> None:
    """关键字管理。"""


@keyword_cmd.command("list")
@click.option("--all", "show_all", is_flag=True, help="包括 disabled")
def list_cmd(show_all: bool) -> None:
    """列出关键字。"""
    init_db()
    with session_scope() as s:
        repo = KeywordRepository(s)
        kws = repo.list(enabled_only=not show_all)
        if not kws:
            click.echo("(no keywords)")
            return
        click.echo(f"{'ID':>4}  {'TERM':<30}  {'WEIGHT':>6}  {'SOURCE':<8}  ENABLED")
        for k in kws:
            click.echo(
                f"{k.id:>4}  {k.term:<30}  {k.weight:>6.2f}  {k.source:<8}  {k.enabled}"
            )


@keyword_cmd.command("add")
@click.argument("term")
@click.option("--weight", default=1.0, type=float, show_default=True)
def add_cmd(term: str, weight: float) -> None:
    """添加关键字。"""
    init_db()
    with session_scope() as s:
        repo = KeywordRepository(s)
        try:
            kw = repo.add(term, weight=weight, source="manual")
            click.echo(f"✓ added #{kw.id} {kw.term} (weight={weight})")
        except Exception as e:
            click.echo(f"✗ {e}", err=True)
            raise click.Abort()


@keyword_cmd.command("del")
@click.argument("term_or_id")
def del_cmd(term_or_id: str) -> None:
    """删除关键字(按 term 或 id)。"""
    init_db()
    parsed_id: int | None = None
    if term_or_id.isdigit():
        parsed_id = int(term_or_id)
    with session_scope() as s:
        repo = KeywordRepository(s)
        ok = repo.delete(parsed_id if parsed_id is not None else term_or_id)
        if ok:
            click.echo(f"✓ deleted {term_or_id}")
        else:
            click.echo(f"✗ not found: {term_or_id}", err=True)
            raise click.Abort()


@keyword_cmd.command("toggle")
@click.argument("term_or_id")
def toggle_cmd(term_or_id: str) -> None:
    """切换 enabled。"""
    init_db()
    parsed_id: int | None = None
    if term_or_id.isdigit():
        parsed_id = int(term_or_id)
    with session_scope() as s:
        repo = KeywordRepository(s)
        kw = repo.toggle(parsed_id if parsed_id is not None else term_or_id)
        if kw is None:
            click.echo(f"✗ not found: {term_or_id}", err=True)
            raise click.Abort()
        click.echo(f"✓ #{kw.id} {kw.term} → enabled={kw.enabled}")