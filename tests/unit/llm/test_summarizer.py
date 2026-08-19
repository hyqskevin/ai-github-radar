"""T130/T137 — llm/summarizer.py 测试。

Mock LLM SDK(openai / anthropic)与 resolve_llm,验证:
- resolve / env fallback
- summarize_repo: provider 分支 + topics 归一化 + 空摘要报错 + 无配置报错
- explain_keyword: happy + 空理由报错
- clean / available_models
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from ai_github_radar.keywords.llm_upgrade import LLMProvider, PROVIDERS
from ai_github_radar.llm import summarizer
from ai_github_radar.llm.summarizer import (
    LLMProviderError,
    available_models,
    explain_keyword,
    resolve_llm,
    summarize_repo,
    _clean_text,
)


def _fake_llm(provider: LLMProvider = LLMProvider.OPENAI) -> SimpleNamespace:
    """一个满足 _ResolvedLLM 属性接口的假对象(避免走 DB)。"""
    spec = PROVIDERS[provider]
    return SimpleNamespace(
        provider=provider,
        model="test-model",
        api_key="sk-test",
        base_url=spec.base_url,
    )


def _fake_openai_response(text: str) -> MagicMock:
    resp = MagicMock()
    msg = MagicMock()
    msg.content = text
    resp.choices = [MagicMock(message=msg)]
    return resp


def _fake_anthropic_response(text: str) -> MagicMock:
    resp = MagicMock()
    resp.content = [MagicMock(text=text)]
    return resp


# ---------------------------------------------------------------------------
# _clean_text
# ---------------------------------------------------------------------------


def test_clean_text_strips_fence_and_collapses() -> None:
    assert _clean_text("```\nhello   world\n```") == "hello world"
    assert _clean_text('"quoted"') == "quoted"
    assert _clean_text("「也能」") == "也能"


# ---------------------------------------------------------------------------
# resolve_llm
# ---------------------------------------------------------------------------


def test_resolve_llm_env_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """无 DB settings 时回退到 env(OPENAI_API_KEY)。"""
    for k in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    with patch.object(summarizer, "_resolve_llm_from_db_settings", return_value=None):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-env")
        resolved = resolve_llm()
    assert resolved is not None
    assert resolved.provider == LLMProvider.OPENAI
    assert resolved.api_key == "sk-env"


def test_resolve_llm_none_when_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    """无任何配置 → None。"""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with patch.object(summarizer, "_resolve_llm_from_db_settings", return_value=None):
        assert resolve_llm() is None


def test_resolve_llm_db_settings_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    """db settings 优先于 env。"""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-env")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    db_llm = _fake_llm(LLMProvider.DEEPSEEK)
    with patch.object(summarizer, "_resolve_llm_from_db_settings", return_value=db_llm):
        resolved = resolve_llm()
    assert resolved.provider == LLMProvider.DEEPSEEK


# ---------------------------------------------------------------------------
# summarize_repo
# ---------------------------------------------------------------------------


def test_summarize_repo_openai_happy() -> None:
    """openai 协议:返回清理后的摘要 + model 标记。"""
    fake = _fake_llm(LLMProvider.OPENAI)
    with patch.object(summarizer, "resolve_llm", return_value=fake), patch(
        "openai.OpenAI"
    ) as openai_cls:
        client = MagicMock()
        client.chat.completions.create.return_value = _fake_openai_response(
            "  一个 Python 异步 Web 框架  "
        )
        openai_cls.return_value = client
        result = summarize_repo(
            full_name="owner/repo",
            description="An async web framework",
            language="Python",
            topics=["web", "python"],
        )
    assert result.summary == "一个 Python 异步 Web 框架"
    assert result.model == "openai/test-model"


def test_summarize_repo_anthropic_happy() -> None:
    """anthropic 协议分支。"""
    fake = _fake_llm(LLMProvider.ANTHROPIC)
    with patch.object(summarizer, "resolve_llm", return_value=fake), patch(
        "anthropic.Anthropic"
    ) as anthropic_cls:
        client = MagicMock()
        client.messages.create.return_value = _fake_anthropic_response("工具链自动化")
        anthropic_cls.return_value = client
        result = summarize_repo(
            full_name="a/b",
            description="tools",
            language="Go",
            topics=None,
        )
    assert result.summary == "工具链自动化"


def test_summarize_repo_no_llm_raises() -> None:
    """无 LLM 配置 → LLMProviderError。"""
    with patch.object(summarizer, "resolve_llm", return_value=None):
        with pytest.raises(LLMProviderError):
            summarize_repo(full_name="a/b", description="d", language="x", topics=None)


def test_summarize_repo_empty_summary_raises() -> None:
    """LLM 返回空 → LLMProviderError。"""
    fake = _fake_llm()
    with patch.object(summarizer, "resolve_llm", return_value=fake), patch(
        "openai.OpenAI"
    ) as openai_cls:
        client = MagicMock()
        client.chat.completions.create.return_value = _fake_openai_response("  ")
        openai_cls.return_value = client
        with pytest.raises(LLMProviderError):
            summarize_repo(full_name="a/b", description="d", language="x", topics=[])


def test_summarize_repo_excerpt_truncated_to_500() -> None:
    """readme_excerpt 超 500 字符被截断。"""
    fake = _fake_llm()
    captured: dict = {}

    def capture(**kwargs):
        captured["messages"] = kwargs.get("messages", [])
        return _fake_openai_response("ok")

    with patch.object(summarizer, "resolve_llm", return_value=fake), patch(
        "openai.OpenAI"
    ) as openai_cls:
        client = MagicMock()
        client.chat.completions.create.side_effect = capture
        openai_cls.return_value = client
        summarize_repo(
            full_name="a/b",
            description="d",
            language="x",
            topics="web,python",
            readme_excerpt="x" * 800,
        )
    user_content = captured["messages"][-1]["content"]
    assert len(user_content) < 800
    assert "read_len" not in user_content  # 模板已格式化


# ---------------------------------------------------------------------------
# explain_keyword
# ---------------------------------------------------------------------------


def test_explain_keyword_happy() -> None:
    """生成 rationale。"""
    fake = _fake_llm()
    with patch.object(summarizer, "resolve_llm", return_value=fake), patch(
        "openai.OpenAI"
    ) as openai_cls:
        client = MagicMock()
        client.chat.completions.create.return_value = _fake_openai_response(
            "说明用户偏向 agent"
        )
        openai_cls.return_value = client
        out = explain_keyword(term="agent", sample_descriptions=["a", "b"], n_stars=2)
    assert out == "说明用户偏向 agent"


def test_explain_keyword_empty_raises() -> None:
    """LLM 空理由 → LLMProviderError。"""
    fake = _fake_llm()
    with patch.object(summarizer, "resolve_llm", return_value=fake), patch(
        "openai.OpenAI"
    ) as openai_cls:
        client = MagicMock()
        client.chat.completions.create.return_value = _fake_openai_response("")
        openai_cls.return_value = client
        with pytest.raises(LLMProviderError):
            explain_keyword(term="x", sample_descriptions=[])


def test_explain_keyword_no_llm_raises() -> None:
    with patch.object(summarizer, "resolve_llm", return_value=None):
        with pytest.raises(LLMProviderError):
            explain_keyword(term="x", sample_descriptions=[])


# ---------------------------------------------------------------------------
# available_models
# ---------------------------------------------------------------------------


def test_available_models_lists_all_providers() -> None:
    out = available_models()
    assert {str(m["provider"]) for m in out} == {
        "openai", "anthropic", "deepseek", "qwen", "moonshot", "zhipu",
    }
    for m in out:
        assert m["default_model"]
        assert m["base_url"].startswith("http")