"""radar web 命令 — T013 占位。"""

from __future__ import annotations

import click


@click.command("web")
@click.option("--host", default="127.0.0.1", show_default=True)
@click.option("--port", default=8765, show_default=True, type=int)
def web_cmd(host: str, port: int) -> None:
    """起本地 Web UI(T013 实装,本 TODO 占位)。"""
    click.echo(
        f"web UI not implemented yet (planned in T013). "
        f"Would bind to http://{host}:{port}"
    )