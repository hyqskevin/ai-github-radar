"""SMTP 邮件推送 — T011.

multipart/alternative (HTML + text),内联 CSS,纯 stdlib (smtplib + email)。
"""

from __future__ import annotations

import html
import logging
import smtplib
import ssl
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, formatdate
from typing import Union

log = logging.getLogger(__name__)


class EmailPushError(Exception):
    """邮件推送失败(网络 / SMTP 异常 / 参数错)。"""


# ---------------------------------------------------------------------------
# 渲染
# ---------------------------------------------------------------------------

_LANG_EMOJI = {
    "python": "🐍", "rust": "🦀", "typescript": "📘", "javascript": "📒",
    "go": "🐹", "java": "☕", "kotlin": "🟪", "swift": "🟧", "ruby": "💎",
    "php": "🐘", "c++": "🔷", "c#": "🎼", "scala": "🔴", "haskell": "🎓",
    "elixir": "💜", "clojure": "🍀", "shell": "🐚", "html": "🌐",
    "css": "🎨", "vue": "🟢",
}


def _lang_emoji(lang: str | None) -> str:
    if not lang:
        return "📦"
    return _LANG_EMOJI.get(lang.lower(), "📦")


def _esc(text: str | None) -> str:
    """HTML 转义用户输入。"""
    if not text:
        return ""
    return html.escape(text, quote=True)


def render_html_email(recs: list[dict], *, date: str) -> str:
    """recs → 内联 CSS HTML body(邮件客户端兼容)。"""
    items_html: list[str] = []
    for r in recs:
        full_name = _esc(r.get("full_name") or f"repo_{r.get('repo_id', 0)}")
        url = f"https://github.com/{full_name}"
        desc = _esc(r.get("description") or "(无描述)")
        lang_emoji = _lang_emoji(r.get("language"))
        score = r.get("score", 0.0)
        stars_today = r.get("stars_today")
        stars_text = f"{stars_today}" if stars_today is not None else "—"
        matched = ", ".join(f"<code>{_esc(k)}</code>" for k in (r.get("matched_keywords") or []))
        if not matched:
            matched = "<em>none</em>"

        items_html.append(f"""
        <div style="margin-bottom: 16px; padding: 12px; border: 1px solid #ddd; border-radius: 6px;">
          <h3 style="margin: 0 0 8px 0; font-family: -apple-system, sans-serif;">
            <a href="{url}" style="color: #0366d6; text-decoration: none;">{full_name}</a>
          </h3>
          <p style="margin: 0 0 8px 0; color: #555;">{desc}</p>
          <p style="margin: 0; font-size: 13px; color: #888;">
            <strong>{lang_emoji}</strong>
            · Score: <code style="background: #f0f0f0; padding: 2px 6px; border-radius: 3px;">{score:.3f}</code>
            · Stars today: {stars_text}
            · Matched: {matched}
          </p>
        </div>
        """)

    if not items_html:
        items_html.append("<p><em>暂无推荐</em></p>")

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>GitHub Radar 推荐 — {date}</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; max-width: 700px; margin: 0 auto; padding: 20px;">
  <h1 style="color: #24292e;">GitHub Radar 推荐 — {date}</h1>
  <p style="color: #666; font-size: 14px;">候选 {len(recs)} 条</p>
  {''.join(items_html)}
  <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
  <p style="color: #999; font-size: 12px;">由 ai-github-radar 自动生成</p>
</body>
</html>
"""


def render_text_email(recs: list[dict], *, date: str) -> str:
    """纯文本 fallback。"""
    lines = [f"GitHub Radar 推荐 — {date}", "", f"候选 {len(recs)} 条", ""]
    for r in recs:
        full_name = r.get("full_name") or f"repo_{r.get('repo_id', 0)}"
        desc = (r.get("description") or "(无描述)").replace("\n", " ")
        score = r.get("score", 0.0)
        lines.append(f"- {full_name}  (score={score:.3f})")
        lines.append(f"  https://github.com/{full_name}")
        if desc:
            lines.append(f"  {desc}")
        lines.append("")
    if not recs:
        lines.append("暂无推荐")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 推送
# ---------------------------------------------------------------------------


def push_email(
    recs: list[dict],
    *,
    smtp_host: str,
    smtp_port: int = 587,
    smtp_user: Union[str, None] = None,
    smtp_password: Union[str, None] = None,
    smtp_to: Union[str, list[str]],
    subject_prefix: str = "[GitHub Radar]",
    use_tls: bool = True,
    timeout: float = 30.0,
) -> dict:
    """SMTP 发送 multipart/alternative 邮件。"""
    # normalize smtp_to
    if isinstance(smtp_to, str):
        to_list = [smtp_to]
    elif isinstance(smtp_to, list) and all(isinstance(x, str) for x in smtp_to):
        to_list = list(smtp_to)
    else:
        raise ValueError(f"smtp_to must be str or list[str], got {type(smtp_to).__name__}")
    if not to_list:
        raise ValueError("smtp_to is empty")

    # render
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    html_body = render_html_email(recs, date=date)
    text_body = render_text_email(recs, date=date)

    # build mime
    msg = MIMEMultipart("alternative")
    from_addr = smtp_user or to_list[0]
    msg["From"] = formataddr(("GitHub Radar", from_addr))
    msg["To"] = ", ".join(to_list)
    msg["Date"] = formatdate(localtime=False)
    msg["Subject"] = f"{subject_prefix} 推荐 — {date}"
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    raw = msg.as_string()

    # send
    try:
        client = smtplib.SMTP(timeout=timeout)
        try:
            client.connect(smtp_host, smtp_port)
            if use_tls:
                context = ssl.create_default_context()
                client.starttls(context=context)
            if smtp_user and smtp_password:
                client.login(smtp_user, smtp_password)
            client.sendmail(from_addr, to_list, raw)
        finally:
            try:
                client.quit()
            except smtplib.SMTPException:
                pass
    except (smtplib.SMTPException, OSError) as e:
        raise EmailPushError(f"SMTP send failed: {e}") from e

    return {
        "to": to_list,
        "subject": msg["Subject"],
        "sent_at": datetime.now(timezone.utc).isoformat(),
    }