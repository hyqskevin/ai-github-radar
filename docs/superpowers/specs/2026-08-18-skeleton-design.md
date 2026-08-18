# Spec — T001 项目骨架

| 维度 | 内容 |
|---|---|
| **TODO ID** | T001（docs/TODO.md §基础设施） |
| **作者** | ai-github-radar 维护者 + AI 助手（2026-08-18） |
| **优先级** | 高 — 阻塞 T002-T019 所有模块 import |
| **触发** | pyproject.toml `[tool.hatch.build.targets.wheel] packages = ["src/ai_github_radar"]` 已声明，但目录不存在，hatchling build 必失败 |

---

## B1. 设计

### 1.1 目标

让 `uv run python -c "import ai_github_radar"`（或宿主 Python：`python3 -c "..."`）从项目根**可成功 import 包**，且 hatchling wheel build 不报错。

### 1.2 文件清单（本次只动 1 个文件）

| 文件 | 操作 | 说明 |
|---|---|---|
| `src/ai_github_radar/__init__.py` | 新建 | 包入口，含 `__version__` |

### 1.3 非目标

- ❌ 不创建子包目录（cli/ / github/ / keywords/ / recommender/ / push/ / db/ / api/）—— 这些是 T002-T015 的活
- ❌ 不写 CLI 入口（pyproject.toml 已声明 `ai_github_radar.cli:app`，但 cli 子包 T012 才建）
- ❌ 不动 pyproject.toml（已含正确依赖 + hatchling 配置）

### 1.4 实现要点

- `__version__ = "0.1.0"` 与 pyproject.toml `[project] version` 保持一致（避免 hatchling 校验失败）
- 模块 docstring 引用 SPEC.md §1 目标 + docs/phase-roadmap.md 阶段一范围
- 不引入任何 import 依赖（保持纯占位）

---

## B2. 验收（AC-N：可观测断言）

| AC | 断言 | 怎么验 |
|---|---|---|
| AC-1 | `python3 -c "import ai_github_radar"` 退出码 0 | `python3 -c "import ai_github_radar"` → echo $? = 0 |
| AC-2 | `ai_github_radar.__version__ == "0.1.0"` | `python3 -c "import ai_github_radar; assert ai_github_radar.__version__ == '0.1.0'"` |
| AC-3 | hatchling build 不报"src/ai_github_radar not found" | `python3 -m hatchling build --target wheel --dry-run`（若 hatchling 不在则用 hatch）→ 0 ERROR |
| AC-4 | 子包目录不存在时 import 不报错 | 当前只有 `__init__.py`，无 cli/ github/ 等子包；AC-4 由 AC-1 间接覆盖 |
| AC-5 | `python3 scripts/audit-loop.py --strict` L0/L4/L7/L8 全 OK | 仓库根跑 |

---

## B3. 测试矩阵（C1-C10 维度）

| C | 维度 | 覆盖 |
|---|---|---|
| C1 功能 | 包可导入 | AC-1 |
| C2 功能 | __version__ 匹配 pyproject | AC-2 |
| C3 边界 | 模块 docstring 非空 | 单测：docstring 首行含 "AI" |
| C4 错误 | 误用 `import ai-github-radar`（连字符）应失败 | 单测：`importlib.import_module("ai-github-radar")` 抛 ModuleNotFoundError |
| C5 一致性 | `__version__` 与 pyproject.toml 同步 | 单测：读 pyproject 解析 version 字段，等于 __version__ |
| C6 性能 | 不引入重依赖（无 numpy/sklearn/GitHub 客户端等 import） | 单测：sys.modules 不含 numpy / sklearn / github |

测试文件：`tests/unit/test_skeleton.py`

---

## B4. 风险

- **R1**：hatchling 在某些版本要求 `src/ai_github_radar/py.typed` 才会构建为 PEP 561 包。**缓解**：阶段一不分发 wheel，hatchling 配置可关闭 strict。AC-3 仅验 build dry-run 跑得通。
- **R2**：未来若加 cli/__init__.py，需要确保 `ai_github_radar.cli:app` 在 pyproject.toml 第 65 行仍可解析。本次不动 cli/，R2 不触发。
- **R3**：`tests/unit/test_skeleton.py` 必须与 `tests/unit/__init__.py` 共存，否则 pytest 在某些版本会报 "no tests ran"。**缓解**：tests/unit/__init__.py 已存在。