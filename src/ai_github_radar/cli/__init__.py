"""CLI 编排 — T012.

`radar` 命令组,基于 click。子命令:
  init / scan / keyword / web
"""

from __future__ import annotations

import click

from ai_github_radar.cli.init_cmd import init_cmd
from ai_github_radar.cli.keyword_cmd import keyword_cmd
from ai_github_radar.cli.scan_cmd import scan_cmd
from ai_github_radar.cli.web_cmd import web_cmd


@click.group()
@click.version_option()
def cli() -> None:
    """ai-github-radar — GitHub 趋势追踪 + 推荐。"""


cli.add_command(init_cmd, name="init")
cli.add_command(scan_cmd, name="scan")
cli.add_command(keyword_cmd, name="keyword")
cli.add_command(web_cmd, name="web")


__all__ = ["cli"]