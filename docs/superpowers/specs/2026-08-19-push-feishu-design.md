# Spec — T010 push/feishu.py

| 维度 | 内容 |
|---|---|
| **TODO ID** | T010（docs/TODO.md §推送） |
| **作者** | ai-github-radar 维护者 + AI 助手（2026-08-19） |
| **优先级** | 中 — 默认走 local,feishu 可选 |
| **触发** | docs/TODO.md T010 |

---

## B1. 设计

### 1.1 目标

实现 `src/ai_github_radar/push/feishu.py`,**飞书自定义机器人 webhook 推送**:

- **消息卡片（interactive）** —— 富文本卡片（标题 + 各 repo 链接 + 元数据）
- **纯文本（text）** —— 兜底,文本模式渲染 Markdown 简化版
- **签名校验** —— 自定义机器人可选签名校验（HMAC-SHA256, timestamp + secret）

### 1.2 API

```python
def push_feishu(
    recs: list[dict],
    *,
    webhook_url: str,
    secret: str | None = None,           # 自定义机器人加签 secret
    message_type: Literal["interactive", "text"] = "interactive",
    timeout: float = 15.0,
    client: httpx.Client | None = None,
) -> dict:
    """POST 到飞书 webhook。返回 webhook 响应 JSON。

    webhook 响应形如:
      {"StatusCode": 0, "msg": "success"}
      {"StatusCode": 1, "msg": "invalid webhook url"}

    抛:
      FeishuPushError: 推送失败(网络 / 非 2xx / StatusCode != 0)
    """

def build_interactive_card(
    recs: list[dict],
    *,
    title: str = "GitHub Radar 推荐",
    date: str,
) -> dict:
    """构造飞书 interactive card payload dict(JSON 序列化后 POST)。"""

def build_text_message(
    recs: list[dict],
    *,
    date: str,
) -> dict:
    """构造 text 类型 payload(纯文本 fallback)。"""
```

### 1.3 非目标

- ❌ 飞书应用机器人(lark SDK,权限更复杂;阶段二 T210)
- ❌ at 全体成员
- ❌ 群自定义关键词触发

---

## B2. 验收

| AC | 断言 | 怎么验 |
|---|---|---|
| AC-1 | `push_feishu` 走 POST 到 webhook_url | respx mock URL 验证 |
| AC-2 | 200 + StatusCode==0 → 返回 dict 不抛错 | respx |
| AC-3 | 非 2xx → FeishuPushError | respx 500 |
| AC-4 | 200 但 StatusCode==1 → FeishuPushError | respx |
| AC-5 | `interactive` 模式 payload 含 msg_type + card | 单测 dict 结构 |
| AC-6 | `text` 模式 payload 含 msg_type=text + text 字段 | 单测 |
| AC-7 | 签名:secret 提供 → payload 含 timestamp + sign | 单测 |
| AC-8 | 签名:无 secret → payload 不含 sign | 单测 |
| AC-9 | HMAC-SHA256 sign 计算正确(基线向量) | 单测 |
| AC-10 | recs 含 score/full_name/description 渲染进 card | 单测 |
| AC-11 | 空 recs → 仍合法 card(只标题 + 0 条) | 单测 |

---

## B3. 测试矩阵

| C | 维度 | 覆盖 |
|---|---|---|
| C1 功能 | POST 行为 | AC-1 |
| C2 错误 | 非 2xx | AC-3 |
| C3 错误 | StatusCode 错误 | AC-4 |
| C4 功能 | interactive payload | AC-5 |
| C5 功能 | text payload | AC-6 |
| C6 边界 | 签名开关 | AC-7 / AC-8 |
| C7 边界 | HMAC 计算 | AC-9 |
| C8 功能 | recs 渲染 | AC-10 |
| C9 边界 | 空 recs | AC-11 |

测试文件：`tests/unit/push/test_feishu.py`

---

## B4. 风险

- **R1**：飞书 webhook 限流(默认 100 req/min)。**缓解**：指数退避 1 次。
- **R2**：签名算法。官方文档：base64(HMAC-SHA256(key=secret, msg=`${timestamp}\n${secret}`).digest())。**缓解**：用 `hmac` + `base64` 标准库。
- **R3**：interactive card schema 字段多（elements / tag / text 等）。**缓解**：用最小 schema,只保留 header + section。