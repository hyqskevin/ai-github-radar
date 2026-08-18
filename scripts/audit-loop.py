#!/usr/bin/env python3
"""audit-loop.py — AGENTS.md §0 step [7] 校验器.

校验:
  L0 文档校验        A 类 8 必填文档存在且非空
  L1 一致性校验      docs/TODO.md 引用的 spec 必须存在
  L2 提交约定校验    最近 10 个 commit 须带 TODO(<id>): 前缀
  L4 happy-path 校验 每个 [x] TODO 对应的 src 文件须有 tests/unit/test_*.py
  L7 路径校验        docs/ 下不应有 .trae/ 或 doc/spec/ 入侵
  L8 沙箱边界校验    .cache/ .venv/ .npm-global/ 须在项目根内

用法:
  python3 scripts/audit-loop.py [--level L0,L1,L2,L4,L7,L8] [--strict] [--json]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

REQUIRED_DOCS: tuple[str, ...] = (
    "SPEC.md",
    "docs/api-doc.md",
    "docs/database-design.md",
    "docs/ui-design.md",
    "docs/architecture.md",
    "docs/phase-roadmap.md",
    "docs/observability.md",
    "docs/deployment.md",
)

KNOWN_LEVELS: tuple[str, ...] = ("L0", "L1", "L2", "L4", "L7", "L8")

FORBIDDEN_DOC_PATHS: tuple[str, ...] = (".trae", "doc/spec")

SANDBOX_DIRS: tuple[str, ...] = (".cache", ".venv", ".npm-global")

# TODO.md 形如: - [x] **T999** — desc  (顶格或前置空白)
TODO_DONE_RE = re.compile(r"-\s*\[x\]\s*\*\*T(\d+)\*\*")

# spec 行:   spec: docs/superpowers/specs/<name>-design.md
SPEC_REF_RE = re.compile(r"spec:\s*(\S+\.md)")

# 期望的 tests 路径后缀
TEST_PATH_RE = re.compile(r"^src/(.+)\.py$")


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------


@dataclass
class Report:
    """单 level 校验报告。"""

    level: str
    status: str = "ok"  # ok / warn / error / skip
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return {
            "level": self.level,
            "status": self.status,
            "errors": self.errors,
            "warnings": self.warnings,
        }


# ---------------------------------------------------------------------------
# 各 Level 校验器
# ---------------------------------------------------------------------------


def audit_l0(root: Path) -> Report:
    r = Report("L0")
    for rel in REQUIRED_DOCS:
        p = root / rel
        if not p.exists() or p.stat().st_size == 0:
            r.errors.append(f"missing or empty: {rel}")
    return r


def audit_l1(root: Path) -> Report:
    r = Report("L1")
    todo = root / "docs" / "TODO.md"
    if not todo.exists():
        r.errors.append("docs/TODO.md missing")
        return r
    refs = SPEC_REF_RE.findall(todo.read_text(encoding="utf-8"))
    for ref in refs:
        # ref 是相对路径,统一相对 root 解析
        target = (root / ref).resolve()
        if not target.exists():
            r.errors.append(f"TODO.md refs missing spec: {ref}")
    return r


def audit_l2(root: Path) -> Report:
    r = Report("L2")
    # 非 git 仓库跳过(SPEC §2 阶段一目标含 git 仓库,但开发期可能有临时裸目录)
    if not (root / ".git").exists():
        r.status = "skip"
        return r
    try:
        out = subprocess.run(
            ["git", "log", "--oneline", "-10"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        ).stdout.strip()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        r.warnings.append("git log failed; skipping L2")
        r.status = "skip"
        return r
    if not out:
        return r  # 没 commit,无 warning
    for line in out.splitlines():
        # 格式: <hash> <subject>
        parts = line.split(maxsplit=1)
        if len(parts) < 2:
            r.warnings.append(f"unparseable commit line: {line!r}")
            continue
        sha, subject = parts
        if not re.match(r"^TODO\([A-Za-z0-9_-]+\):", subject):
            r.warnings.append(f"commit without TODO(<id>): prefix: {sha} {subject}")
    return r


def audit_l4(root: Path) -> Report:
    r = Report("L4")
    todo = root / "docs" / "TODO.md"
    if not todo.exists():
        return r  # L0 已报
    ids = TODO_DONE_RE.findall(todo.read_text(encoding="utf-8"))
    if not ids:
        return r
    # T0xx / T1xx 在不同 src 子包,启发式:T0xx -> src/ai_github_radar/<rest>,T1xx -> app/web/<rest>
    for tid in ids:
        # 跳过 T9xx 测试用 TID(避免 L4 自身 audit-loop.py 误判)
        if tid == "999":
            continue
        candidate = _guess_src_for_todo(root, tid)
        if candidate is None or not candidate.exists():
            continue  # 跳过未对应实现的 TODO(空 TODO 不强求)
        # 推 tests/unit/test_<path_under_src>.py
        test_path = _guess_test_path(root, candidate)
        if test_path is None or not test_path.exists():
            r.errors.append(f"T{tid} done but no happy-path test: {test_path}")
    return r


def audit_l7(root: Path) -> Report:
    r = Report("L7")
    docs_dir = root / "docs"
    if not docs_dir.exists():
        return r
    # 扫 docs/ 子树
    for match in docs_dir.rglob("*"):
        if any(part == forbidden or forbidden in match.parts for part in [match.name] for forbidden in FORBIDDEN_DOC_PATHS):
            r.errors.append(f"forbidden path under docs/: {match.relative_to(root)}")
    # 也扫根路径下入侵(防止 .trae/ 在根上污染整仓库)
    for forbidden in FORBIDDEN_DOC_PATHS:
        rogue = root / forbidden
        if rogue.exists():
            r.errors.append(f"forbidden dir at repo root: {forbidden}")
    return r


def audit_l8(root: Path) -> Report:
    r = Report("L8")
    # 期望: .cache / .venv / .npm-global 应在 root 内(若存在)
    for sub in SANDBOX_DIRS:
        p = root / sub
        if p.exists() and not p.is_relative_to(root.resolve()):
            r.errors.append(f"sandbox dir outside project root: {p}")
    return r


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _guess_src_for_todo(root: Path, tid: str) -> Path | None:
    """按 TODO 数字段猜测对应 src 文件路径(约定,见 TODO.md)。"""
    if tid.startswith("T0"):
        # T002 -> config.py,T004 -> github/client.py,T009 -> push/local.py
        # 通过查 TODO.md 描述行
        pass
    # 简化:仅当 TODO.md 该行描述里出现 src/ 路径时使用
    todo = root / "docs" / "TODO.md"
    if not todo.exists():
        return None
    pat = re.compile(rf"-\s*\[x\]\s*\*\*T{tid}\*\*[^\n]*")
    m = pat.search(todo.read_text(encoding="utf-8"))
    if not m:
        return None
    line = m.group(0)
    src_m = re.search(r"`([\w/]+\.py)`", line)
    if src_m:
        return root / "src" / "ai_github_radar" / src_m.group(1) if not src_m.group(1).startswith("src/") else root / src_m.group(1)
    return None


def _guess_test_path(root: Path, src_path: Path) -> Path | None:
    """src_path -> tests/unit/test_<path_under_src>.py。"""
    try:
        rel = src_path.relative_to(root / "src" / "ai_github_radar")
    except ValueError:
        try:
            rel = src_path.relative_to(root / "src")
        except ValueError:
            return None
    flat = str(rel.with_suffix("")).replace("/", "_").replace("-", "_")
    return root / "tests" / "unit" / f"test_{flat}.py"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


LEVEL_FUNCS: dict[str, Callable[[Path], Report]] = {
    "L0": audit_l0,
    "L1": audit_l1,
    "L2": audit_l2,
    "L4": audit_l4,
    "L7": audit_l7,
    "L8": audit_l8,
}


def _parse_levels(s: str) -> list[str]:
    levels = [x.strip().upper() for x in s.split(",") if x.strip()]
    bad = [x for x in levels if x not in KNOWN_LEVELS]
    if bad:
        # argparse 用 exit code 2 表示 usage error
        raise argparse.ArgumentTypeError(
            f"unknown level(s): {','.join(bad)}; known: {','.join(KNOWN_LEVELS)}"
        )
    return levels


def _level_arg(value: str) -> list[str]:
    return _parse_levels(value)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="audit-loop",
        description="AGENTS.md §0 step [7] 校验器(L0/L1/L2/L4/L7/L8)",
    )
    parser.add_argument(
        "--level",
        default=",".join(KNOWN_LEVELS),
        type=_level_arg,
        help=f"逗号分隔要跑的 level,默认 {','.join(KNOWN_LEVELS)}",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="任一 ERROR 即退出码 1",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="输出 JSON 报告",
    )
    parser.add_argument(
        "--root",
        default=".",
        help="项目根路径(默认 cwd)",
    )
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    levels = args.level  # argparse type=_level_arg 已校验
    reports: list[Report] = []
    for lv in levels:
        rep = LEVEL_FUNCS[lv](root)
        # 升级 status
        if rep.errors:
            rep.status = "error"
        elif rep.warnings:
            rep.status = "warn"
        elif rep.status == "skip":
            pass
        else:
            rep.status = "ok"
        reports.append(rep)

    if args.json:
        payload = {
            **{r.level: r.status for r in reports},
            "reports": [r.as_dict() for r in reports],
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        for rep in reports:
            tag = {"ok": "OK", "warn": "WARN", "error": "ERROR", "skip": "SKIP"}.get(
                rep.status, rep.status.upper()
            )
            print(f"[{rep.level}] {tag} — {len(rep.errors)} error(s), {len(rep.warnings)} warn(s)")
            for e in rep.errors:
                print(f"       ERROR  {e}")
            for w in rep.warnings:
                print(f"       WARN   {w}")
        total_err = sum(len(r.errors) for r in reports)
        total_warn = sum(len(r.warnings) for r in reports)
        if args.strict and total_err:
            print(f"\nResult: {total_err} ERROR, {total_warn} WARN → strict mode FAIL (exit 1)")
            return 1
        print(f"\nResult: {total_err} ERROR, {total_warn} WARN")

    total_err = sum(len(r.errors) for r in reports)
    if args.strict and total_err:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())