"""T010 push/feishu.py 测试。

用 httpx.MockTransport 直接注入响应(避免 respx + httpx.Client 拦截问题)。
"""

from __future__ import annotations

import base64
import hashlib
import hmac
from typing import Callable

import httpx
import pytest

from ai_github_radar.push.feishu import (
    FeishuPushError,
    _sign_payload,
    build_interactive_card,
    build_text_message,
    push_feishu,
)


WEBHOOK = "https://open.feishu.cn/open-apis/bot/v2/hook/test-token"
SECRET = "test_secret_for_sign"


SAMPLE_RECS = [
    {
        "repo_id": 100, "full_name": "owner1/repo1",
        "description": "Python FastAPI web framework",
        "language": "Python", "score": 12.34,
        "matched_keywords": ["fastapi"], "rank": 1, "stars_today": 200,
    },
    {
        "repo_id": 200, "full_name": "owner2/repo2",
        "description": "Rust async runtime",
        "language": "Rust", "score": 9.5,
        "matched_keywords": ["async"], "rank": 2, "stars_today": 80,
    },
]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _make_client(handler: Callable[[httpx.Request], httpx.Response]) -> httpx.Client:
    """构造带 mock transport 的 httpx.Client,所有请求走 handler。"""
    transport = httpx.MockTransport(handler)
    return httpx.Client(transport=transport, timeout=10.0)


# ---------------------------------------------------------------------------
# build_interactive_card
# ---------------------------------------------------------------------------


def test_ac5_interactive_card_payload() -> None:
    """AC-5: interactive card 含 msg_type=interactive + card。"""
    card = build_interactive_card(SAMPLE_RECS, date="2026-08-19")
    assert card["msg_type"] == "interactive"
    assert "card" in card
    assert card["card"]["header"]["title"]["content"] == "GitHub Radar 推荐 — 2026-08-19"
    assert len(card["card"]["elements"]) > 0


def test_ac10_recs_rendered_into_card() -> None:
    """AC-10: recs 内容渲染进 card。"""
    import json
    card = build_interactive_card(SAMPLE_RECS, date="2026-08-19")
    blob = json.dumps(card, ensure_ascii=False)
    assert "owner1/repo1" in blob
    assert "owner2/repo2" in blob


def test_ac11_empty_recs_produces_valid_card() -> None:
    """AC-11: 空 recs 合法 card。"""
    card = build_interactive_card([], date="2026-08-19")
    assert card["msg_type"] == "interactive"
    assert "card" in card


# ---------------------------------------------------------------------------
# build_text_message
# ---------------------------------------------------------------------------


def test_ac6_text_payload() -> None:
    """AC-6: text 类型 payload。"""
    msg = build_text_message(SAMPLE_RECS, date="2026-08-19")
    assert msg["msg_type"] == "text"
    assert "text" in msg
    assert "owner1/repo1" in msg["text"]["content"]


# ---------------------------------------------------------------------------
# push_feishu — 网络层
# ---------------------------------------------------------------------------


def test_ac2_200_with_statuscode_0_returns_dict() -> None:
    """AC-2: 200 + StatusCode==0 返 dict。"""
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"StatusCode": 0, "msg": "ok"})
    client = _make_client(handler)
    out = push_feishu(SAMPLE_RECS, webhook_url=WEBHOOK, client=client)
    assert out == {"StatusCode": 0, "msg": "ok"}


def test_ac3_non_2xx_raises_feishu_error() -> None:
    """AC-3: 非 2xx → FeishuPushError。"""
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(500)
    client = _make_client(handler)
    with pytest.raises(FeishuPushError):
        push_feishu(SAMPLE_RECS, webhook_url=WEBHOOK, client=client,
                    _retry_sleep=lambda _: None)


def test_ac4_statuscode_1_raises_feishu_error() -> None:
    """AC-4: StatusCode==1 → FeishuPushError。"""
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"StatusCode": 1, "msg": "invalid"})
    client = _make_client(handler)
    with pytest.raises(FeishuPushError):
        push_feishu(SAMPLE_RECS, webhook_url=WEBHOOK, client=client,
                    _retry_sleep=lambda _: None)


def test_429_retries_then_succeeds() -> None:
    """429 重试 1 次后 200 成功。"""
    call_count = {"n": 0}

    def handler(req: httpx.Request) -> httpx.Response:
        call_count["n"] += 1
        if call_count["n"] == 1:
            return httpx.Response(429)
        return httpx.Response(200, json={"StatusCode": 0, "msg": "ok"})
    client = _make_client(handler)
    out = push_feishu(SAMPLE_RECS, webhook_url=WEBHOOK, client=client,
                      _retry_sleep=lambda _: None)
    assert call_count["n"] == 2
    assert out["StatusCode"] == 0


def test_429_retries_then_500_raises() -> None:
    """429 + 500(连续失败) → FeishuPushError。"""
    call_count = {"n": 0}

    def handler(req: httpx.Request) -> httpx.Response:
        call_count["n"] += 1
        if call_count["n"] == 1:
            return httpx.Response(429)
        return httpx.Response(500)
    client = _make_client(handler)
    with pytest.raises(FeishuPushError):
        push_feishu(SAMPLE_RECS, webhook_url=WEBHOOK, client=client,
                    _retry_sleep=lambda _: None)


# ---------------------------------------------------------------------------
# 签名
# ---------------------------------------------------------------------------


def test_ac7_with_secret_payload_includes_sign() -> None:
    """AC-7: secret 提供 → payload 含 timestamp + sign。"""
    card = build_interactive_card(SAMPLE_RECS, date="2026-08-19")
    ts = "1700000000"
    signed = _sign_payload(card, secret=SECRET, timestamp=ts)
    assert signed.get("timestamp") == ts
    assert "sign" in signed
    assert len(signed["sign"]) > 20


def test_ac8_without_secret_no_sign() -> None:
    """AC-8: 无 secret → 无 sign。"""
    card = build_interactive_card(SAMPLE_RECS, date="2026-08-19")
    signed = _sign_payload(card, secret=None, timestamp="123")
    assert "sign" not in signed
    assert "timestamp" not in signed


def test_ac9_hmac_sha256_baseline() -> None:
    """AC-9: HMAC-SHA256 sign 与基线一致。"""
    payload = {"x": 1}
    ts = "1700000000"
    signed = _sign_payload(payload, secret=SECRET, timestamp=ts)
    expected = base64.b64encode(
        hmac.new(SECRET.encode(), f"{ts}\n{SECRET}".encode(), hashlib.sha256).digest()
    ).decode()
    assert signed["sign"] == expected


def test_push_feishu_with_secret_sends_sign() -> None:
    """push_feishu(secret=...) → POST body 含 sign 字段。"""
    captured = {}

    def handler(req: httpx.Request) -> httpx.Response:
        captured["body"] = req.content
        return httpx.Response(200, json={"StatusCode": 0, "msg": "ok"})
    client = _make_client(handler)
    push_feishu(SAMPLE_RECS, webhook_url=WEBHOOK, client=client, secret=SECRET)
    import json
    body = json.loads(captured["body"])
    assert "sign" in body
    assert "timestamp" in body
    # 验证签名正确
    ts = body["timestamp"]
    expected = base64.b64encode(
        hmac.new(SECRET.encode(), f"{ts}\n{SECRET}".encode(), hashlib.sha256).digest()
    ).decode()
    assert body["sign"] == expected


def test_push_feishu_text_mode() -> None:
    """message_type=text → POST body msg_type=text。"""
    captured = {}

    def handler(req: httpx.Request) -> httpx.Response:
        captured["body"] = req.content
        return httpx.Response(200, json={"StatusCode": 0, "msg": "ok"})
    client = _make_client(handler)
    push_feishu(SAMPLE_RECS, webhook_url=WEBHOOK, client=client, message_type="text")
    import json
    body = json.loads(captured["body"])
    assert body["msg_type"] == "text"


def test_push_feishu_default_uses_interactive() -> None:
    """默认 message_type=interactive。"""
    captured = {}

    def handler(req: httpx.Request) -> httpx.Response:
        captured["body"] = req.content
        return httpx.Response(200, json={"StatusCode": 0, "msg": "ok"})
    client = _make_client(handler)
    push_feishu(SAMPLE_RECS, webhook_url=WEBHOOK, client=client)
    import json
    body = json.loads(captured["body"])
    assert body["msg_type"] == "interactive"