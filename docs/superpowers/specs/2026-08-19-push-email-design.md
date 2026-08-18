# Spec — T011 push/email.py

| 维度 | 内容 |
|---|---|
| **TODO ID** | T011（docs/TODO.md §推送） |
| **作者** | ai-github-radar 维护者 + AI 助手（2026-08-19） |
| **优先级** | 低 — 邮件不是首选 |
| **触发** | docs/TODO.md T011 |

---

## B1. 设计

### 1.1 目标

实现 `src/ai_github_radar/push/email.py`,**SMTP 邮件推送**:

- **HTML body** —— 复用 Markdown 内容,内联 CSS 转 HTML（避免外部 CSS 加载）
- **plain text fallback** —— 兼容不支持 HTML 的客户端
- **配置来自 T002 Settings** —— `smtp_host / smtp_port / smtp_user / smtp_password / smtp_to`

### 1.2 API

```python
def render_html_email(
    recs: list[dict],
    *,
    date: str,
) -> str:
    """recs → 内联 CSS 的 HTML body。"""

def render_text_email(
    recs: list[dict],
    *,
    date: str,
) -> str:
    """纯文本 fallback。"""

def push_email(
    recs: list[dict],
    *,
    smtp_host: str,
    smtp_port: int = 587,
    smtp_user: str | None = None,
    smtp_password: str | None = None,
    smtp_to: list[str] | str,
    subject_prefix: str = "[GitHub Radar]",
    use_tls: bool = True,
    timeout: float = 30.0,
) -> dict:
    """SMTP 发送 multipart/alternative 邮件(HTML + text)。

    返回 dict:{"to": [...], "subject": "...", "sent_at": "..."}
    抛 EmailPushError。
    """
```

### 1.3 非目标

- ❌ 邮件模板引擎(jinja2 → HTML 不必要,内联 CSS 字符串模板足够)
- ❌ 附件 / 图片内嵌
- ❌ OAuth SMTP(Gmail OAuth 阶段二)
- ❌ 邮件队列(阶段二)

---

## B2. 验收

| AC | 断言 | 怎么验 |
|---|---|---|
| AC-1 | render_html_email 含 `<html>` + 内联 CSS | 单测 |
| AC-2 | recs full_name / description / score 渲染进 HTML | 单测 |
| AC-3 | language emoji (T009 复用) 在 HTML 中 | 单测 |
| AC-4 | render_text_email 纯文本,无 `<` 字符 | 单测 |
| AC-5 | push_email 调用 smtplib.SMTP() 且 login + sendmail | mock smtplib |
| AC-6 | smtp_password 提供 → 走 login | mock |
| AC-7 | smtp_password=None → 不 login(匿名,少见但允许) | mock |
| AC-8 | use_tls=True 走 starttls | mock |
| AC-9 | smtp_to 是 str → list 化;list 直接用 | 单测 |
| AC-10 | 失败(SMTP 异常)→ EmailPushError | mock raise |
| AC-11 | 返回 dict 含 to / subject / sent_at | 单测 |
| AC-12 | multipart/alternative 含 text/plain + text/html | mock 检查 message |

---

## B3. 测试矩阵

| C | 维度 | 覆盖 |
|---|---|---|
| C1 功能 | HTML 渲染 | AC-1 / AC-2 / AC-3 |
| C2 功能 | text 渲染 | AC-4 |
| C3 网络 | SMTP 调用 | AC-5 |
| C4 配置 | password 开关 | AC-6 / AC-7 |
| C5 配置 | TLS | AC-8 |
| C6 边界 | smtp_to str/list | AC-9 |
| C7 错误 | SMTP 异常 | AC-10 |
| C8 一致性 | 返回 dict | AC-11 |
| C9 结构 | multipart | AC-12 |

测试文件：`tests/unit/push/test_email.py`(mock smtplib 不实发)

---

## B4. 风险

- **R1**：smtplib 测试 —— mock `smtplib.SMTP` 类,用 `unittest.mock.patch`。
- **R2**：multipart 构造 —— 用 `email.mime.multipart.MIMEMultipart` + `MIMEText(text, "plain")` + `MIMEText(html, "html")`。
- **R3**：starttls 调用顺序 —— connect → ehlo → starttls → login → sendmail。
- **R4**：HTML 注入 —— full_name / description 用户输入,需要 `html.escape()` 转义避免 XSS。