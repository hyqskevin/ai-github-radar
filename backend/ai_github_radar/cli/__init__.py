"""CLI 编排 — T012.

`radar` 命令组,基于 click。子命令:
  init / scan / keyword / web
"""

from __future__ import annotations

import click

from ai_github_radar.cli import init_cmd, keyword_cmd, scan_cmd, web_cmd


@click.group()
@click.version_option()
def cli() -> None:
    """ai-github-radar — GitHub 趋势追踪 + 推荐。"""


cli.add_command(init_cmd.cmd_init, name="init")
cli.add_command(scan_cmd.cmd_scan, name="scan")
cli.add_command(keyword_cmd.keyword_cmd, name="keyword")
cli.add_command(web_cmd.web_cmd, name="web")


__all__ = ["cli"]