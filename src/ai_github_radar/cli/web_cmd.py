"""radar web 命令 — T013 起 FastAPI."""

from __future__ import annotations

import click


@click.command("web")
@click.option("--host", default="127.0.0.1", show_default=True)
@click.option("--port", default=8765, show_default=True, type=int)
def web_cmd(host: str, port: int) -> None:
    """起本地 Web UI(FastAPI + uvicorn)。"""
    from ai_github_radar.web import run_server
    click.echo(f"→ starting web UI at http://{host}:{port} (Ctrl-C to quit)")
    run_server(host=host, port=port)