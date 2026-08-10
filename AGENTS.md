# AGENTS.md — AI 协作 Loop(项目无关版)

> 本文件是所有 AI 助手(Codex / Claude Code / Cursor / Copilot 等)进入项目**必须先读**的硬约束。
> 把 `TODO → spec → TDD → impl → audit` 这条流水线固化成 8 步 loop。
> 本文件随项目 `git init` 提交,不随会话结束而消失。
>
> **本文件只写脚手架架构 / loop 流程 / 反模式 / 沙箱约束**。具体内容(13 维度 / 目录结构 / Python 栈 / doc-fetcher 流程) 见:
> - 13 维度全表 → [docs/dimensions.md](./docs/dimensions.md)
> - 前后端目录 → [docs/structure.md](./docs/structure.md)
> - 沙箱行为 → [docs/sandbox-behavior.md](./docs/sandbox-behavior.md)
> - 工具手册 → [docs/tool-manual-preflight.md](./docs/tool-manual-preflight.md)
> - Python 栈 → [docs/python-stack.md](./docs/python-stack.md)

---

## 0. Loop 总览(8 步严格按顺序)

```
[1] 文档前置        A1-A6 + A8 + A9 必填(7 份);A7/A10/A11/A12/A13 提示型
                    ↓
                    audit-loop.py L0 校验:docs/ + SPEC.md 全在,缺一拒绝
   ↓
[2] TODO 提出       docs/TODO.md 新增 [ ] 条目(目标 / 验收 AC-N / spec 链接 / 测试维度)
   ↓
[3] spec 设计       docs/superpowers/specs/<date>-<slug>-design.md
                    (B1 设计 / B2 验收 AC-N / B3 测试矩阵)
   ↓
[4] TDD 红         tests/unit/ + tests/e2e/ 写测试(按 C1-C10 维度挑)
   ↓
[5] 实现→绿        写代码让测试 PASS
   ↓
[6] 重构           测试保护下重构
   ↓
[7] audit          python3 scripts/audit-loop.py --strict
                    (L0 文档 / L1 一致性 / L2 提交 / L4 happy-path / L7 路径 / L8 边界)
   ↓
[8] commit         TODO(<id>): <动词> <对象>;core hook 强制前缀
```

**任何一步缺失都要暂停补齐**;**A 类 8 必填文档不全** = 项目未就绪 = **禁止开始任何 TODO 实现**。
具体维度 / 模板 / 速查表全部在 [docs/dimensions.md](./docs/dimensions.md) —— 本文件不重复。

---

## 1. 持续授权的边界

**默认授权**(无需逐项询问):
- 按 docs/TODO.md 当前 [ ] 顺序推进
- 写 spec 后默认视为已审核,直接进入 TDD
- 在项目目录内创建/修改常规文件
- 跑本地测试、起本地服务

**必须暂停询问**:
- 需要新的外部账号 / 凭证 / 验证码
- 删除生产数据、对外发布、付费操作、不可逆动作
- TODO 存在歧义且无法从现有 spec / 代码 / 文档确定
- 用户主动撤回持续授权

---

## 2. TDD 硬规则

- 测试先写 → 看到红 → 实现 → 看到绿 → 重构
- 每个 TODO 至少 1 个单元测试 + 1 个 E2E 用例(spec 里说明豁免例外)
- mock 占比 ≤ 测试用例的 30%(防止"局部最优":只测 mock 协议,没测真实路径)
- 错误路径必须有测试(空值 / 权限 / 异常 / 边界)
- "没写测试" = "没做完"

详细模板见 `tests/_TEMPLATE.md`(10 维度全覆盖)+ `tests/unit/_TEMPLATE.py` + `tests/frontend/_TEMPLATE.{vue,react,svelte,vanilla}.spec.ts`。

---

## 3. 反模式与拦截

| 反模式 | 表现 | 兜底 |
|---|---|---|
| 跳过 spec 直写代码 | commit 引用了不存在的 spec | pre-commit + CI 拒绝 |
| 只写 happy path | 测试无错误分支 | audit-loop 检测 happy-path-only |
| 局部最优 | 改了 API 但 UI 没接 / DB 列加了但服务没读 | audit-loop 检测 orphan endpoint / orphan column |
| 冗余代码 | import / 函数没人调用 | audit-loop 检测 unused imports / dead functions |
| TODO 漂移 | commit 改了代码但 TODO.md 没动 | pre-commit 检测 staged diff vs TODO.md |
| 偷工减料 | spec 验收只写"实现即可" | spec 模板强制 `AC-N: <可观测断言>` |
| 设计文档写到 .trae / doc/spec/ | IDE 抢文档路径 | audit-loop L7 ERROR |
| 产物写到 ~/ / /etc / shell config | 污染用户目录 | audit-loop L8 + sandbox-detect |

---

## 4. 提问与回答

若用户问"为什么"或质疑"原因":
1. **先排查证据**(读代码 / 跑测试 / 看日志 / 看 DB)
2. **找到真正根因**(不止表面现象)
3. **给方案**(不只是 `延长超时` 这种 workaround)
4. 在持续授权范围内直接进入 spec + TDD;若会改变需求边界则暂停询问

---

## 5. 撤销不符合规则的代码

任何**缺 spec / TDD 未完成 / 验收未达**的代码:
- 立即撤掉(revert 或物理删除)
- 用户否决 spec 时,连 spec 一起撤
- 不允许"先合并再补"

---

## 6. 沙箱硬约束(产物边界)

> **核心规则**:脚手架的所有产物**必须**落在 **项目目录 + 系统 /tmp**;
> **绝不**写到 `~/` / `~/.config/` / `/etc/` / PATH 配置文件(`.bashrc` / `.zshrc` / `.profile` / `/etc/paths.d`)。

**允许写入** `$ROOT/` `$ROOT/.cache/` `$ROOT/.venv/` `$ROOT/.npm-global/` `/tmp/`
**严禁写入** `~/.local/` `~/Library/Caches/` `~/.bashrc` `~/.zshrc` `/etc/`

**两层防护**:
1. **启动时锁死**(`setup-python.sh` / `setup-node.sh` 头部设 6 个环境变量 → UV_CACHE_DIR / PLAYWRIGHT_BROWSERS_PATH / NPM_CONFIG_CACHE / PIP_CACHE_DIR / UV_PYTHON_INSTALL_DIR / TMPDIR)
2. **运行时检测**(`scripts/sandbox-detect.sh` 9 项 + `audit-loop L8` 项目边界)

完整列表 / 兼容性矩阵 / 降级策略见 [docs/sandbox-behavior.md](./docs/sandbox-behavior.md)。

---

## 7. 提交约定

- commit message 首行格式: `TODO(<id>): <动词> <对象>`
  - 例: `TODO(007): add dedupe-by-normalized-title service`
- 一条 commit 只做一件事,关联一条 TODO id
- 不允许出现没有 `TODO(<id>):` 前缀的 commit(本地 hook 警告 / CI 阻断)

---

## 8. 阶段管理

- 阶段一:本地优先,单机可跑(SQLite / filesystem broker / 本地文件存储)
- 阶段二:容器化(Docker Compose / 外部 broker / DB / 对象存储)
- 阶段切换通过 `docs/phase-roadmap.md` 跟踪,每个阶段结束跑一次 `audit-loop.py --strict` + 全量回归

---

## 9. 例外条款(必须显式记录)

任何**违反 §0-§8 的行为**必须:
1. PR 描述里写明**为什么** + **影响范围**
2. `docs/architecture.md` 加一条 ADR 记录决策
3. `docs/TODO.md` 加一条 `[ ]` 跟进(revert / 补规格 / 重构)

**不允许** "先 commit 再补 doc" / "其他项目也这么做" / "review 时再说" —— commit 时刻就要合规。