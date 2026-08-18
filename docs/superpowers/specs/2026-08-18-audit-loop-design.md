# Spec — `scripts/audit-loop.py` (L0/L1/L2/L4/L7/L8 校验器)

> **AGENTS.md §0 step [7]**：`python3 scripts/audit-loop.py --strict`
> 校验本文档存在性 / 一致性 / 提交合规 / happy-path 测试存在 / 路径边界 / 产物边界。

| 维度 | 内容 |
|---|---|
| **TODO ID** | PRE-001（前置于 docs/TODO.md T001-T019，作为 §0 [7] 校验器基础设施） |
| **作者** | ai-github-radar 维护者 + AI 助手（2026-08-18） |
| **优先级** | 高 — 没有它 AGENTS.md §0 [7] 无法执行，8 步 loop 闭环断 |
| **触发** | AGENTS.md §0 强制要求 `audit-loop.py` 存在，§0 L0/L1/L2/L4/L7/L8 校验全部依赖 |

---

## B1. 设计

### 1.1 目标

实现 `scripts/audit-loop.py`，按 AGENTS.md §0 step [7] 跑：
- **L0 文档校验**：A 类 8 必填文档（SPEC.md / docs/api-doc.md / docs/database-design.md / docs/ui-design.md / docs/architecture.md / docs/phase-roadmap.md / docs/observability.md / docs/deployment.md）全部存在且非空
- **L1 一致性校验**：`docs/TODO.md` 引用的 `docs/superpowers/specs/*.md` 必须存在（防止 §3「跳过 spec 直写代码」反模式）
- **L2 提交约定校验**：检查最近 N 个 commit 是否带 `TODO(<id>):` 前缀（防止 §7「偷前缀」反模式）
- **L4 happy-path 校验**：每个已完成 TODO（docs/TODO.md `[x]`）对应的 src/ 文件必须有 `tests/unit/test_*.py` 覆盖 happy-path（防止 §3「只写 happy path」反模式遗漏 happy 覆盖）
- **L7 路径校验**：检查 `docs/` 下不存在以 `.trae/` `doc/spec/` 开头的路径（防止 IDE 抢文档路径）
- **L8 沙箱边界校验**：检查 `.cache/` `.venv/` `.npm-global/` 等产物目录在项目根内（防止污染 `~/` / `~/.config/` / `/etc/`）

### 1.2 非目标

- ❌ 不跑代码 lint（ruff/mypy 由各自工具负责）
- ❌ 不跑测试（pytest 自己负责）
- ❌ 不做代码覆盖率统计（pytest --cov 负责）
- ❌ 不修改文件（只读 + 报告）

### 1.3 架构

单文件 Python 3.12 脚本，标准库 only（`pathlib` / `re` / `subprocess` / `argparse` / `sys`）。零依赖。

```
audit-loop.py
├── argparse:  --strict, --level L0/L1/L2/L4/L7/L8, --json
├── audit():
│   ├── L0_required_docs()      → list[str] (缺失路径)
│   ├── L1_spec_consistency()   → list[str] (TODO.md 引用了不存在的 spec)
│   ├── L2_commit_prefix()      → list[str] (commit 缺 TODO(<id>): 前缀)
│   ├── L4_happy_path_tests()   → list[str] (TODO 完成但缺 happy-path 测试)
│   ├── L7_doc_path_breach()    → list[str] (.trae/ / doc/spec/ 入侵)
│   └── L8_sandbox_boundary()   → list[str] (产物目录不在项目根内)
└── main():     跑 --level 指定的校验 → 打印报告 → 退出码 0/1
```

### 1.4 CLI 契约

```
python3 scripts/audit-loop.py [--level L0,L1,L2,L4,L7,L8] [--strict] [--json]
```

| 参数 | 默认 | 说明 |
|---|---|---|
| `--level` | `L0,L1,L2,L4,L7,L8` | 逗号分隔要跑的校验 |
| `--strict` | False | True 时任一 ERROR 即退出码 1；默认 WARN 不阻断 |
| `--json` | False | 输出 JSON 报告 |

**退出码**：
- 0：全部 OK 或仅有 WARN
- 1：--strict 模式下有 ERROR

### 1.5 输出格式

人类可读（默认）：
```
[L0] OK — 8/8 required docs present
[L1] OK — 0/5 TODO.md spec refs missing
[L2] WARN — 2/10 commits without TODO(<id>): prefix
       - abc1234 fix typo
       - def5678 update readme
[L4] ERROR — 3/19 done TODOs lack happy-path test
       - T004: github/client.py  →  no tests/unit/test_github_client.py
[L7] OK — no .trae/ or doc/spec/ paths
[L8] OK — .cache/ .venv/ inside project root

Result: 1 ERROR, 2 WARN → strict mode FAIL (exit 1)
```

JSON（`--json`）：
```json
{"L0": "ok", "L1": "ok", "L2": "warn", "L4": "error", "L7": "ok", "L8": "ok", "errors": [...], "warnings": [...]}
```

---

## B2. 验收（AC-N：可观测断言）

| AC | 断言 | 怎么验 |
|---|---|---|
| AC-1 | 仓库完整时（删 `--strict`）退出码 0 | `cd repo && python3 scripts/audit-loop.py` → `echo $?` = 0 |
| AC-2 | 缺 SPEC.md 时（`mv SPEC.md /tmp/`）报 L0 ERROR | 移走 SPEC.md 再跑 → stdout 含 `[L0] ERROR — missing SPEC.md` |
| AC-3 | TODO.md 引用不存在的 spec 时报 L1 ERROR | 在 TODO.md 加一行引用 `nonexistent-spec.md`，跑 → stdout 含 `[L1] ERROR` |
| AC-4 | 跑 `--strict` 且有 L4 ERROR 时退出码 1 | 完成 T004 但不写测试，跑 → `echo $?` = 1 |
| AC-5 | 检测到 `.trae/spec.md` 时报 L7 ERROR | `mkdir -p .trae && touch .trae/x.md`，跑 → stdout 含 `[L7] ERROR` |
| AC-6 | `--json` 输出合法 JSON 且包含 6 个 level key | 跑 → `python3 -c "import json,sys; d=json.loads(sys.stdin.read()); assert set(d) >= {'L0','L1','L2','L4','L7','L8'}"` |
| AC-7 | --level L0 只跑 L0 不报 L4 | 跑 `python3 scripts/audit-loop.py --level L0` → stdout 无 `[L4]` |
| AC-8 | 在 git 仓库里能解析最近 10 个 commit | `git log --oneline -10` 看得到，audit 也跑得过 L2 |

---

## B3. 测试矩阵（C1-C10 维度）

| C | 维度 | 覆盖 |
|---|---|---|
| C1 功能 | 必填文档检测 | AC-2 |
| C2 功能 | spec 一致性检测 | AC-3 |
| C3 功能 | commit 前缀检测 | AC-8 + 单测（构造 mock commit log）|
| C4 功能 | happy-path 测试存在性检测 | AC-4 + 单测 |
| C5 功能 | 路径越界检测 | AC-5 |
| C6 功能 | 沙箱边界检测 | 单测：临时建 `~/.config/radar-test-marker`（应 ERROR，因为脚本检测到 ~/.config 写入意图） |
| C7 边界 | 空仓库（无 git） | L2 跳过返回 ok |
| C8 边界 | 无 docs/ 目录 | L0 全部 ERROR |
| C9 错误 | --level 含未知 level | argparse error 退出码 2 |
| C10 输出 | --json 合法 | AC-6 |

测试文件：`tests/unit/scripts/test_audit_loop.py`（用 subprocess 跑 audit-loop.py，monkeypatch 改文件树）

---

## B4. 实现细节备忘

- L2 用 `subprocess.run(["git", "log", "--oneline", "-10"])`，捕获输出，解析每行首字段
- L8 检查 `$ROOT/.cache/` `.venv/` `.npm-global/` 存在性 → 必须都在 `$ROOT/` 内（用 `Path.resolve()` 与 `$ROOT.resolve()` 比前缀）
- L4 解析 `docs/TODO.md` 找 `- [x] **Txxx**`，再在 `src/ai_github_radar/<...>.py` 找对应文件，最后查 `tests/unit/test_<...>.py` 是否存在
- 单文件实现，控制在 250 行内

---

## B5. 风险

- **R1**：L4 解析 `src/ai_github_radar/github/client.py` ↔ `tests/unit/test_github_client.py` 路径映射靠约定，不写复杂 AST。若重构路径，audit 需要同步更新。**缓解**：用 `src_path.replace("/", "_").replace(".py", "")` 推 test 路径，并在 WARN 中报告推断依据。
- **R2**：L2 只检查最近 10 个 commit。**缓解**：用 `--level L2` 单独跑或未来加 `--all` flag（不在本次范围）。
- **R3**：纯标准库实现，subprocess 调 git 在 Windows 上路径处理复杂。**缓解**：阶段一目标 macOS / Linux，不支持 Windows（SPEC §2 非目标）。