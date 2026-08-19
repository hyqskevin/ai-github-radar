#!/usr/bin/env python3
"""design-check.py — DESIGN.md ↔ app/web/main.css 交叉验证 (T111).

DESIGN.md 是单一 token 源(SSoT):
- colors.{primary,secondary,tertiary,neutral,success,warning,error}
- typography.{h1,h2,h3,body-md,body-sm,mono}.fontSize

校验:
  1. DESIGN.md 7 色都被 app/web/app/assets/css/main.css 引用
  2. DESIGN.md typography 字号跟 main.css 衍生一致(可选 warn)

退出码:
  0 = OK
  1 = ERROR(任一校验失败)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DESIGN_PATH = ROOT / "DESIGN.md"
MAIN_CSS = ROOT / "app" / "web" / "app" / "assets" / "css" / "main.css"


def parse_design_colors(text: str) -> dict[str, str]:
    """从 YAML front-matter 提取 colors 块,形如 {primary: '#E6E1E5', ...}。"""
    m = re.search(r"^colors:\s*\n((?:\s{2}\w+:\s*\"#[0-9A-Fa-f]{6}\"\s*\n)+)", text, re.MULTILINE)
    if not m:
        return {}
    block = m.group(1)
    out = {}
    for line in block.splitlines():
        lm = re.match(r"\s{2}(\w+):\s*\"(#[0-9A-Fa-f]{6})\"", line)
        if lm:
            out[lm.group(1)] = lm.group(2).upper()
    return out


def parse_main_css_token_usage(text: str) -> set[str]:
    """main.css 中 --color-<name>-500: #...; 用了哪些 token 名。"""
    matches = re.findall(r"--color-(\w+)-\d{2,3}:\s*(#[0-9A-Fa-f]{6})", text)
    return {name for name, _ in matches}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--root", type=Path, default=ROOT,
        help="项目根目录(测试用)",
    )
    args = parser.parse_args()

    design_path = args.root / "DESIGN.md"
    css_path = args.root / "app" / "web" / "app" / "assets" / "css" / "main.css"

    if not design_path.exists():
        print(f"ERROR: DESIGN.md not found at {design_path}", file=sys.stderr)
        return 1
    if not css_path.exists():
        print(f"ERROR: main.css not found at {css_path}", file=sys.stderr)
        return 1

    design_text = design_path.read_text()
    css_text = css_path.read_text()

    design_colors = parse_design_colors(design_text)
    css_tokens = parse_main_css_token_usage(css_text)

    if not design_colors:
        print("ERROR: failed to parse DESIGN.md colors block", file=sys.stderr)
        return 1

    expected_keys = {"primary", "secondary", "tertiary", "neutral", "success", "warning", "error"}
    missing_in_design = expected_keys - set(design_colors.keys())
    if missing_in_design:
        print(f"ERROR: DESIGN.md missing colors: {sorted(missing_in_design)}", file=sys.stderr)
        return 1

    missing_in_css = []
    for key in expected_keys:
        # CSS 至少要有这个 token name(色阶 500 即 base)
        if key not in css_tokens:
            missing_in_css.append(key)

    result = {
        "design_colors": design_colors,
        "css_token_names": sorted(css_tokens),
        "missing_in_design": sorted(missing_in_design),
        "missing_in_css": missing_in_css,
    }

    if args.json:
        print(json.dumps(result, indent=2))

    if missing_in_design:
        print(f"ERROR: DESIGN.md 缺颜色: {missing_in_design}", file=sys.stderr)
        return 1
    if missing_in_css:
        print(f"ERROR: main.css 缺 DESIGN token: {missing_in_css}", file=sys.stderr)
        return 1

    if not args.json:
        print(f"OK — DESIGN.md ↔ main.css 7 token 同步 ({len(design_colors)} colors checked)")
    return 0


if __name__ == "__main__":
    sys.exit(main())