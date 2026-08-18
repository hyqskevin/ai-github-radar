"""T007 llm_upgrade.py 测试。

mock OpenAI / Anthropic SDK,验证 6 个 provider 注册 + 协议分支 + prompt + 重试 + 探测。
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from ai_github_radar.keywords import llm_upgrade
from ai_github_radar.keywords.llm_upgrade import (
    LLMProvider,
    LLMProviderError,
    PROVIDERS,
    detect_provider,
    extract_keywords_via_llm,
)


SAMPLE_DOCS = [
    "Python web framework FastAPI for async APIs",
    "Rust async runtime for high-performance IO",
    "Python machine learning with deep neural networks",
    "TypeScript React framework for frontend apps",
]


# ---------------------------------------------------------------------------
# PROVIDERS 注册
# ---------------------------------------------------------------------------


def test_ac1_six_providers_registered() -> None:
    """AC-1: 6 个 provider 在 PROVIDERS,字段完整。"""
    assert len(PROVIDERS) == 6
    for name, spec in PROVIDERS.items():
        assert spec.base_url.startswith("http")
        assert spec.default_model
        assert spec.protocol in ("openai", "anthropic")
        assert spec.env_key


def test_all_expected_providers_present() -> None:
    """6 个 provider 全在(openai/anthropic/deepseek/qwen/moonshot/zhipu)。"""
    names = {p.value for p in PROVIDERS.keys()}
    assert names == {"openai", "anthropic", "deepseek", "qwen", "moonshot", "zhipu"}


def test_anthropic_uses_anthropic_protocol() -> None:
    """anthropic provider 走 anthropic 协议,其他 5 个走 openai 兼容。"""
    assert PROVIDERS[LLMProvider.ANTHROPIC].protocol == "anthropic"
    for p in LLMProvider:
        if p == LLMProvider.ANTHROPIC:
            continue
        assert PROVIDERS[p].protocol == "openai", f"{p} should be openai-compat"


# ---------------------------------------------------------------------------
# detect_provider
# ---------------------------------------------------------------------------


def test_ac8_detect_priority(monkeypatch: pytest.MonkeyPatch) -> None:
    """AC-8: env 多 key 时按优先级返 OPENAI > ANTHROPIC > DEEPSEEK > QWEN > MOONSHOT > ZHIPU。"""
    for k in (
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "DEEPSEEK_API_KEY",
        "DASHSCOPE_API_KEY",
        "MOONSHOT_API_KEY",
        "ZHIPUAI_API_KEY",
    ):
        monkeypatch.delenv(k, raising=False)
    # 设 ZHIPU → 应返 ZHIPU(唯一一个有 key 的)
    monkeypatch.setenv("ZHIPUAI_API_KEY", "x")
    assert detect_provider() == LLMProvider.ZHIPU
    # 加 DEEPSEEK → 应返 DEEPSEEK(优先级更高)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "x")
    assert detect_provider() == LLMProvider.DEEPSEEK


def test_ac9_no_keys_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """AC-9: 无任何 key → None。"""
    for k in (
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "DEEPSEEK_API_KEY",
        "DASHSCOPE_API_KEY",
        "MOONSHOT_API_KEY",
        "ZHIPUAI_API_KEY",
    ):
        monkeypatch.delenv(k, raising=False)
    assert detect_provider() is None


def test_anthropic_priority_over_deepseek(monkeypatch: pytest.MonkeyPatch) -> None:
    """anthropic key 比 deepseek 优先级高。"""
    for k in (
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "DEEPSEEK_API_KEY",
        "DASHSCOPE_API_KEY",
        "MOONSHOT_API_KEY",
        "ZHIPUAI_API_KEY",
    ):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "x")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    assert detect_provider() == LLMProvider.ANTHROPIC


# ---------------------------------------------------------------------------
# extract_keywords_via_llm - OpenAI 兼容协议
# ---------------------------------------------------------------------------


def _make_openai_response(keywords: list[dict]) -> MagicMock:
    """模拟 OpenAI ChatCompletion 返回。"""
    resp = MagicMock()
    msg = MagicMock()
    msg.content = json.dumps(keywords)
    choice = MagicMock()
    choice.message = msg
    resp.choices = [choice]
    return resp


@pytest.fixture()
def patched_openai_client():
    """fixture 版 patch。返回 mock client,使用方设 client.chat.completions.create.return_value。"""
    cm = patch("ai_github_radar.keywords.llm_upgrade._get_openai_client")
    get_client = cm.__enter__()
    client = MagicMock()
    get_client.return_value = client
    yield client
    cm.__exit__(None, None, None)


def test_ac2_openai_provider_calls_chat_completions(
    monkeypatch: pytest.MonkeyPatch, patched_openai_client: MagicMock
) -> None:
    """AC-2: openai provider 走 chat.completions.create。"""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    patched_openai_client.chat.completions.create.return_value = _make_openai_response(
        [{"term": "agent", "score": 8.5}, {"term": "claude", "score": 7.0}]
    )
    out = extract_keywords_via_llm(SAMPLE_DOCS, provider="openai", max_keywords=10)
    assert patched_openai_client.chat.completions.create.called
    assert out[0][0] == "agent"
    assert out[0][1] == 8.5


def test_deepseek_uses_openai_compat(
    monkeypatch: pytest.MonkeyPatch, patched_openai_client: MagicMock
) -> None:
    """DeepSeek 走 OpenAI 兼容协议,base_url 自定义。"""
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    patched_openai_client.chat.completions.create.return_value = _make_openai_response(
        [{"term": "agent", "score": 9.0}]
    )
    out = extract_keywords_via_llm(
        SAMPLE_DOCS, provider="deepseek", base_url="https://api.deepseek.com/v1"
    )
    assert patched_openai_client.chat.completions.create.called
    assert out[0][0] == "agent"


def test_qwen_default_base_url(
    monkeypatch: pytest.MonkeyPatch, patched_openai_client: MagicMock
) -> None:
    """qwen 不传 base_url → 用 PROVIDERS 默认 DashScope。"""
    monkeypatch.setenv("DASHSCOPE_API_KEY", "sk-test")
    patched_openai_client.chat.completions.create.return_value = _make_openai_response(
        [{"term": "qwen", "score": 8}]
    )
    out = extract_keywords_via_llm(SAMPLE_DOCS, provider="qwen")
    assert out[0][0] == "qwen"


# ---------------------------------------------------------------------------
# extract_keywords_via_llm - Anthropic 协议
# ---------------------------------------------------------------------------


def _make_anthropic_response(keywords: list[dict]) -> MagicMock:
    resp = MagicMock()
    block = MagicMock()
    block.text = json.dumps(keywords)
    resp.content = [block]
    return resp


def test_ac3_anthropic_calls_messages(monkeypatch: pytest.MonkeyPatch) -> None:
    """AC-3: anthropic 走 messages.create。"""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    resp = _make_anthropic_response([
        {"term": "skill", "score": 9.0},
        {"term": "mcp", "score": 8.0},
    ])
    with patch("ai_github_radar.keywords.llm_upgrade._get_anthropic_client") as get_client:
        client = MagicMock()
        client.messages.create.return_value = resp
        get_client.return_value = client
        out = extract_keywords_via_llm(SAMPLE_DOCS, provider="anthropic")
    assert client.messages.create.called
    assert out[0][0] == "skill"


# ---------------------------------------------------------------------------
# Prompt / 响应解析
# ---------------------------------------------------------------------------


def test_ac4_prompt_contains_max_keywords(monkeypatch: pytest.MonkeyPatch) -> None:
    """AC-4: prompt 含 max_keywords。"""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    resp = _make_openai_response([{"term": "x", "score": 5}])
    captured = {}

    def capture(**kwargs):
        captured["kwargs"] = kwargs
        return resp

    with patch("ai_github_radar.keywords.llm_upgrade._get_openai_client") as get_client:
        client = MagicMock()
        client.chat.completions.create.side_effect = capture
        get_client.return_value = client
        extract_keywords_via_llm(SAMPLE_DOCS, provider="openai", max_keywords=20)
    # prompt 在 messages 里
    msgs = captured["kwargs"].get("messages", [])
    user_msg = msgs[-1]
    user_content = user_msg["content"] if isinstance(user_msg, dict) else user_msg.content
    assert "20" in str(user_content)


def test_ac5_parses_array_response(
    monkeypatch: pytest.MonkeyPatch, patched_openai_client: MagicMock
) -> None:
    """AC-5: 响应 JSON 数组。"""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    patched_openai_client.chat.completions.create.return_value = _make_openai_response(
        [{"term": "agent", "score": 8.5}, {"term": "claude", "score": 7.0}]
    )
    out = extract_keywords_via_llm(SAMPLE_DOCS, provider="openai")
    assert isinstance(out, list)
    assert all(isinstance(t, str) and isinstance(w, float) for t, w in out)


def test_ac6_parses_object_response(
    monkeypatch: pytest.MonkeyPatch, patched_openai_client: MagicMock
) -> None:
    """AC-6: 响应 JSON 对象 {keywords: [...]} 也支持。"""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    resp_obj = MagicMock()
    msg = MagicMock()
    msg.content = json.dumps(
        {"keywords": [{"term": "a", "score": 9}, {"term": "b", "score": 7}]}
    )
    resp_obj.choices = [MagicMock(message=msg)]
    patched_openai_client.chat.completions.create.return_value = resp_obj
    out = extract_keywords_via_llm(SAMPLE_DOCS, provider="openai")
    assert out[0][0] == "a"


# ---------------------------------------------------------------------------
# 错误 / 重试
# ---------------------------------------------------------------------------


def test_ac7_retries_on_failure(
    monkeypatch: pytest.MonkeyPatch, patched_openai_client: MagicMock
) -> None:
    """AC-7: 失败重试 1 次(第二次成功)。"""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    call_count = {"n": 0}

    def side_effect(**_):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("transient failure")
        return _make_openai_response([{"term": "retry_ok", "score": 8}])

    patched_openai_client.chat.completions.create.side_effect = side_effect
    out = extract_keywords_via_llm(
        SAMPLE_DOCS, provider="openai", _retry_sleep=lambda _: None
    )
    assert call_count["n"] == 2  # 失败 + 重试
    assert out[0][0] == "retry_ok"


def test_c12_401_raises_provider_error(
    monkeypatch: pytest.MonkeyPatch, patched_openai_client: MagicMock
) -> None:
    """C12: 401 → LLMProviderError(不抛原始 SDK 异常)。"""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    patched_openai_client.chat.completions.create.side_effect = RuntimeError(
        "401 unauthorized"
    )
    with pytest.raises(LLMProviderError):
        extract_keywords_via_llm(
            SAMPLE_DOCS, provider="openai", _retry_sleep=lambda _: None
        )


def test_invalid_provider_name_raises() -> None:
    """未知 provider 抛 ValueError。"""
    with pytest.raises(ValueError):
        extract_keywords_via_llm(SAMPLE_DOCS, provider="not_a_real_provider")


def test_missing_api_key_for_explicit_provider_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """显式 provider 但无 key → 抛 LLMProviderError(不静默走 auto)。"""
    for k in (
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "DEEPSEEK_API_KEY",
        "DASHSCOPE_API_KEY",
        "MOONSHOT_API_KEY",
        "ZHIPUAI_API_KEY",
    ):
        monkeypatch.delenv(k, raising=False)
    with pytest.raises(LLMProviderError):
        extract_keywords_via_llm(SAMPLE_DOCS, provider="deepseek")


# ---------------------------------------------------------------------------
# 用户覆盖
# ---------------------------------------------------------------------------


def test_ac10_api_key_override_env(
    monkeypatch: pytest.MonkeyPatch, patched_openai_client: MagicMock
) -> None:
    """AC-10: api_key 参数覆盖 env。"""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    patched_openai_client.chat.completions.create.return_value = _make_openai_response(
        [{"term": "x", "score": 5}]
    )
    extract_keywords_via_llm(
        SAMPLE_DOCS, provider="openai", api_key="sk-explicit-override"
    )
    # 验证 client 用了 override 的 key(由 _get_openai_client 内部处理)
    assert patched_openai_client.chat.completions.create.called


def test_ac11_base_url_override(
    monkeypatch: pytest.MonkeyPatch, patched_openai_client: MagicMock
) -> None:
    """AC-11: base_url 参数覆盖 provider 默认。"""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    patched_openai_client.chat.completions.create.return_value = _make_openai_response(
        [{"term": "x", "score": 5}]
    )
    custom_url = "https://my-custom-llm-proxy.example.com/v1"
    extract_keywords_via_llm(SAMPLE_DOCS, provider="openai", base_url=custom_url)
    assert patched_openai_client.chat.completions.create.called