# A2 接口设计 — ai-github-radar CLI

> CLI 子命令的完整契约。阶段一无 HTTP API（CLI 工具，不暴露服务端点）。

## 子命令总览

```
ai-github-radar
├── init                    # 首次运行：拉 star + 提取关键字
├── scan                    # 单次扫描 trending + 匹配 + 推送
├── daemon                  # 周期守护（前台运行）
├── keyword
│   ├── list                # 列关键字
│   ├── add <term>          # 加关键字
│   ├── del <id|term>       # 删关键字
│   └── toggle <id|term>    # 启用/停用
├── history                 # 历史推荐回顾
└── config                  # 看 / 校验配置
```

## init

```
ai-github-radar init [--user <name>] [--no-llm] [--force]
```

| 参数 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| `--user` | str | 否 | $RADAR_USER | GitHub username，覆盖 .env |
| `--no-llm` | flag | 否 | False | 禁用 LLM，只用 TF-IDF |
| `--force` | flag | 否 | False | 清空 stars 表重建 |

**输出**：标准输出报告拉了多少 star、提取了多少关键字。

**退出码**：
- 0：成功
- 1：参数错
- 2：GitHub API 错（401/403/429）
- 3：DB 写失败

## scan

```
ai-github-radar scan [--limit N] [--push <target>] [--lang <list>] [--dry-run]
```

| 参数 | 类型 | 默认 | 说明 |
|---|---|---|---|
| `--limit` | int | 20 | 最多推 N 条 |
| `--push` | str | $RADAR_PUSH_TARGET | local / feishu / email |
| `--lang` | str | "" | 限定语言（逗号分隔） |
| `--dry-run` | flag | False | 只打印，不推送、不入库 |

**输出**：
```
[1] obra/superpowers ⭐269,881
    匹配关键字: agent, skill, claude (score=8.5)
    https://github.com/obra/superpowers
    ...
```

## daemon

```
ai-github-radar daemon [--interval <daily|weekly>] [--dry-run]
```

前台运行，asyncio 循环，按 `--interval` 调 `scan`。`Ctrl-C` 退出。

## keyword

```
ai-github-radar keyword list [--json] [--enabled-only]

ai-github-radar keyword add <term> [--weight 1.0] [--source auto|manual]

ai-github-radar keyword del <id|term>

ai-github-radar keyword toggle <id|term>
```

| 参数 | 说明 |
|---|---|
| `--weight` | 1.0 = 默认，> 1 权重更高 |
| `--source` | `auto` = init 时 TF-IDF 自动提的，`manual` = 用户手加 |

## history

```
ai-github-radar history [--since 30d] [--limit 50] [--json]
```

显示过去 N 天已推送过的推荐（去重）。

## config

```
ai-github-radar config [--show] [--validate]
```

- `--show`：打印当前生效配置（隐藏 token）
- `--validate`：跑 Pydantic 校验，配置不对报具体错

## 全局选项

```
--config <path>     # 指定 .env 路径（默认 ./config/.env）
--log-level <lvl>   # DEBUG/INFO/WARNING/ERROR
--no-color          # 关闭 Rich 颜色
--version
--help
```

## 错误约定

- 致命错（无法继续）：stderr 输出 + 退出码非 0
- 警告（可继续）：stderr 一行黄字
- 信息：stdout

## 测试覆盖

- [ ] 每个子命令至少有 1 个 `tests/cli/test_<subcmd>.py` 用 respx mock GitHub API
- [ ] `--dry-run` 行为必须测试
- [ ] 错误退出码必须测试