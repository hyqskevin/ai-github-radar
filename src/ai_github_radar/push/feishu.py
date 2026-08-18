"""飞书 webhook 推送 — T010.

支持 interactive 卡片 + text 文本 + HMAC-SHA256 签名。
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import time
from typing import Callable, Literal, Optional

import httpx

log = logging.getLogger(__name__)


UA = "ai-github-radar/0.1"
DEFAULT_TIMEOUT = 15.0

MessageType = Literal["interactive", "text"]


class FeishuPushError(Exception):
    """飞书推送失败(网络 / 非 2xx / StatusCode != 0)。"""


# ---------------------------------------------------------------------------
# 构造 payload
# ---------------------------------------------------------------------------


def build_interactive_card(
    recs: list[dict],
    *,
    date: str,
    title: str = "GitHub Radar 推荐",
) -> dict:
    """飞书 interactive card(最小 schema: header + 多个 section)。"""
    sections: list[dict] = []
    for r in recs:
        full_name = r.get("full_name") or f"unknown/repo_{r.get('repo_id', 0)}"
        html_url = f"https://github.com/{full_name}"
        desc = r.get("description") or "(无描述)"
        score = r.get("score", 0.0)
        stars_today = r.get("stars_today")
        stars_text = f"{stars_today}" if stars_today is not None else "—"
        matched = r.get("matched_keywords") or []
        matched_text = " · ".join(matched) if matched else "—"

        section = {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": (
                    f"**[{full_name}]({html_url})**\n"
                    f"{desc}\n"
                    f"\n"
                    f"Score: `{score:.3f}`  ·  Stars today: `{stars_text}`  ·  "
                    f"Matched: `{matched_text}`"
                ),
            },
        }
        sections.append(section)

    if not sections:
        sections.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": "_暂无推荐_"},
        })

    return {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"{title} — {date}",
                }
            },
            "elements": sections,
        },
    }


def build_text_message(recs: list[dict], *, date: str) -> dict:
    """text 类型 payload(纯文本 fallback)。"""
    lines = [f"GitHub Radar 推荐 — {date}\n"]
    for r in recs:
        full_name = r.get("full_name") or f"unknown/repo_{r.get('repo_id', 0)}"
        desc = (r.get("description") or "").replace("\n", " ")
        score = r.get("score", 0.0)
        lines.append(f"- [{full_name}](https://github.com/{full_name}) (score={score:.3f})")
        if desc:
            lines.append(f"  {desc}")
    if not recs:
        lines.append("_暂无推荐_")
    return {
        "msg_type": "text",
        "text": {"content": "\n".join(lines)},
    }


# ---------------------------------------------------------------------------
# 签名
# ---------------------------------------------------------------------------


def _sign_payload(
    payload: dict,
    *,
    secret: Optional[str],
    timestamp: Optional[str] = None,
) -> dict:
    """添加 timestamp + sign 字段(如有 secret)。

    官方算法:
      string_to_sign = f"{timestamp}\n{secret}"
      hmac_code = hmac.new(secret.encode(), string_to_sign.encode(), sha256).digest()
      sign = base64(hmac_code)
    """
    if not secret:
        return dict(payload)
    ts = timestamp or str(int(time.time()))
    string_to_sign = f"{ts}\n{secret}"
    hmac_code = hmac.new(
        secret.encode("utf-8"),
        string_to_sign.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    sign = base64.b64encode(hmac_code).decode("utf-8")
    out = dict(payload)
    out["timestamp"] = ts
    out["sign"] = sign
    return out


# ---------------------------------------------------------------------------
# push
# ---------------------------------------------------------------------------


def push_feishu(
    recs: list[dict],
    *,
    webhook_url: str,
    secret: Optional[str] = None,
    message_type: MessageType = "interactive",
    timeout: float = DEFAULT_TIMEOUT,
    client: Optional[httpx.Client] = None,
    _retry_sleep: Callable[[float], None] = time.sleep,
) -> dict:
    """POST 到飞书 webhook。返回响应 JSON dict。

    抛 FeishuPushError。
    """
    if message_type == "interactive":
        payload = build_interactive_card(recs, date=_today_iso())
    else:
        payload = build_text_message(recs, date=_today_iso())

    payload = _sign_payload(payload, secret=secret)

    headers = {"User-Agent": UA, "Content-Type": "application/json"}
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    own_client = client is None
    if own_client:
        client = httpx.Client(timeout=timeout, headers=headers)

    last_err: Optional[Exception] = None
    try:
        for attempt in range(2):  # 1 initial + 1 retry
            try:
                resp = client.post(webhook_url, content=body)
                if resp.status_code >= 500:
                    last_err = FeishuPushError(f"webhook {resp.status_code}: {resp.text[:200]}")
                    _retry_sleep(1.0)
                    continue
                if resp.status_code == 429:
                    _retry_sleep(1.0)
                    continue
                resp.raise_for_status()
                data = resp.json()
                status = data.get("StatusCode", 0) if isinstance(data, dict) else 0
                if status != 0:
                    raise FeishuPushError(
                        f"feishu StatusCode={status}: {data.get('msg') if isinstance(data, dict) else data}"
                    )
                return data if isinstance(data, dict) else {"raw": data}
            except FeishuPushError:
                raise
            except (httpx.HTTPError, ValueError) as e:
                last_err = e
                _retry_sleep(1.0)
                continue
        raise FeishuPushError(f"feishu push failed after 2 attempts: {last_err}")
    finally:
        if own_client:
            client.close()


def _today_iso() -> str:
    """今天 UTC,YYYY-MM-DD。"""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")