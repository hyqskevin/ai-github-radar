"""LLM 仓库简介 / 关键字 rationale — T130.

复用 keywords/llm_upgrade 的多 provider 调用栈,生成两类内容:

1. **Star.summary**:基于仓库 description + topics + language + readme 前 500 字,
   生成 1-3 句中文摘要(用户能在列表页一眼看懂这个仓库干嘛的)。
2. **Keyword.rationale**:解释 LLM 为何提取这个关键字(基于用户 star 仓库的整体画像)。

配置优先级(对齐 runner.run_init):
  1. SQLite settings (前端 /api/settings/llm 写的)
  2. .env (T007 的 *_API_KEY)
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Optional

from ai_github_radar.keywords.llm_upgrade import (
    LLMProvider,
    LLMProviderError,
    PROVIDERS,
    detect_provider,
)

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class SummaryResult:
    """仓库摘要生成结果。"""

    summary: str
    model: str  # 实际用的模型(provider/model)


# ---------------------------------------------------------------------------
# Provider / API key 解析
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _ResolvedLLM:
    provider: LLMProvider
    model: str
    api_key: str
    base_url: Optional[str] = None


def _resolve_llm_from_db_settings() -> Optional[_ResolvedLLM]:
    """从 SQLite settings 表读 provider/model/api_key(用户在前端配的)。"""
    from ai_github_radar.services.settings import (
        KEY_LLM_API_KEY,
        KEY_LLM_MODEL,
        KEY_LLM_PROVIDER,
        get_setting,
    )
    from ai_github_radar.storage.db import session_scope

    try:
        with session_scope() as s:
            provider_str = (get_setting(s, KEY_LLM_PROVIDER, "") or "").strip()
            model = (get_setting(s, KEY_LLM_MODEL, "") or "").strip()
            api_key = (get_setting(s, KEY_LLM_API_KEY, "") or "").strip()
    except Exception:  # noqa: BLE001
        return None

    if not provider_str or provider_str == "none":
        return None
    if not api_key:
        return None
    try:
        provider = LLMProvider(provider_str)
    except ValueError:
        log.warning("settings llm.provider=%r unknown", provider_str)
        return None
    spec = PROVIDERS[provider]
    return _ResolvedLLM(
        provider=provider,
        model=model or spec.default_model,
        api_key=api_key,
    )


def _resolve_llm_from_env() -> Optional[_ResolvedLLM]:
    """从 .env / 进程 env 找(向后兼容 T007)。"""
    p = detect_provider()
    if p is None:
        return None
    spec = PROVIDERS[p]
    return _ResolvedLLM(
        provider=p,
        model=spec.default_model,
        api_key=os.environ.get(spec.env_key, "") or "",
    )


def resolve_llm() -> Optional[_ResolvedLLM]:
    """db settings 优先 → env fallback。"""
    return _resolve_llm_from_db_settings() or _resolve_llm_from_env()


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------


_SUMMARY_SYSTEM = (
    "你是一名资深 GitHub 项目作者,擅长用一两句中文精准概括仓库的核心价值。"
    "摘要必须客观,基于提供的 description + topics + README,不夸大,不编造。"
)

_SUMMARY_USER_TEMPLATE = """请基于以下 GitHub 仓库元数据,生成 1-3 句中文摘要(总字数 50-120 字)。

仓库: {full_name}
主语言: {language}
Topics: {topics}
Description: {description}

README 摘要(前 {read_len} 字符):
{readme_excerpt}

严格要求:
1. 只输出摘要文本本身,不要任何前缀("该仓库..."、"总之")、不要 markdown、不要项目符号
2. 抓核心功能 + 技术栈 + 适用场景
3. 如 README 摘要为空,就只基于 description 写
"""


_RATIONALE_SYSTEM = (
    "你是一名 GitHub 用户画像分析专家。"
    "你会基于用户 star 过的仓库清单,解释为何某个技术关键词对这位用户重要。"
)

_RATIONALE_USER_TEMPLATE = """用户 star 了 {n_stars} 个仓库,涵盖技术栈大致如下(每行一个,逗号分隔 topic/语言):

{samples}

请解释为什么 "{term}" 这个关键词会从用户的 star 列表中被提取出来(1-2 句中文,20-60 字)。

要求:
1. 直接说明该关键词在用户兴趣中的角色(信号/偏好/方向)
2. 不必复述仓库名字,直击技术关联
3. 只输出解释文本,不要任何前缀
"""


# ---------------------------------------------------------------------------
# API 调用(OpenAI 兼容 / Anthropic — 与 llm_upgrade 共用底层,但允许单独指定 model/api_key)
# ---------------------------------------------------------------------------


def _call_chat(
    llm: _ResolvedLLM,
    system: str,
    user: str,
    *,
    timeout: float = 30.0,
    temperature: float = 0.3,
    max_tokens: int = 512,
) -> str:
    """调一次 chat completion,返回 assistant 文本。

    - 复用 llm_upgrade 的协议分支(openai / anthropic)
    - 重试 1 次(等 1 秒)
    """
    spec = PROVIDERS[llm.provider]
    last_err: Optional[Exception] = None
    for attempt in range(2):
        try:
            if spec.protocol == "openai":
                import openai
                client = openai.OpenAI(
                    api_key=llm.api_key,
                    base_url=llm.base_url or spec.base_url,
                    timeout=timeout,
                )
                resp = client.chat.completions.create(
                    model=llm.model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return (resp.choices[0].message.content or "").strip()
            else:  # anthropic
                import anthropic
                client = anthropic.Anthropic(
                    api_key=llm.api_key,
                    base_url=llm.base_url or spec.base_url,
                    timeout=timeout,
                )
                resp = client.messages.create(
                    model=llm.model,
                    max_tokens=max_tokens,
                    system=system,
                    messages=[{"role": "user", "content": user}],
                    temperature=temperature,
                )
                if resp.content:
                    return resp.content[0].text.strip()
                return ""
        except Exception as e:  # noqa: BLE001
            last_err = e
            log.warning(
                "LLM summary call attempt %d failed (%s): %s",
                attempt + 1, llm.provider.value, e,
            )
            if attempt == 0:
                import time as _time_mod
                _time_mod.sleep(1.0)
    raise LLMProviderError(
        f"summary call failed after 2 attempts: {last_err}"
    ) from last_err


def _clean_text(s: str) -> str:
    """去 LLM 输出里的多余空白 + markdown 噪音。"""
    if not s:
        return ""
    s = re.sub(r"^```[a-zA-Z]*\n?|```$", "", s.strip())
    # 去首尾引号
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("「") and s.endswith("」")):
        s = s[1:-1]
    # 多余空白压成单空格(保留换行)
    s = re.sub(r"[ \t]+", " ", s)
    return s.strip()


# ---------------------------------------------------------------------------
# 主 API
# ---------------------------------------------------------------------------


def summarize_repo(
    *,
    full_name: str,
    description: Optional[str],
    language: Optional[str],
    topics: list[str] | str | None,
    readme_excerpt: str = "",
    timeout: float = 30.0,
) -> SummaryResult:
    """生成 1-3 句中文摘要。无 LLM 配置时抛 LLMProviderError。

    - topics 接受 list 或 comma-separated str 或 None
    - readme_excerpt 截前 500 字
    """
    llm = resolve_llm()
    if llm is None:
        raise LLMProviderError(
            "no LLM configured — set provider + api_key in /settings or .env"
        )

    if isinstance(topics, list):
        topics_str = ", ".join(t for t in topics if t) or "(none)"
    elif isinstance(topics, str) and topics:
        topics_str = topics
    else:
        topics_str = "(none)"

    desc_str = (description or "").strip() or "(no description)"
    lang_str = (language or "").strip() or "unknown"
    excerpt = (readme_excerpt or "")[:500].strip() or "(README 不可用)"

    user_prompt = _SUMMARY_USER_TEMPLATE.format(
        full_name=full_name,
        language=lang_str,
        topics=topics_str,
        description=desc_str,
        readme_excerpt=excerpt,
        read_len=len(excerpt),
    )

    raw = _call_chat(llm, _SUMMARY_SYSTEM, user_prompt, timeout=timeout, max_tokens=300)
    summary = _clean_text(raw)

    if not summary:
        raise LLMProviderError("LLM returned empty summary")

    return SummaryResult(
        summary=summary,
        model=f"{llm.provider.value}/{llm.model}",
    )


def explain_keyword(
    *,
    term: str,
    sample_descriptions: list[str],
    n_stars: int = 0,
    timeout: float = 20.0,
) -> str:
    """为某关键字生成 1-2 句「为何提取它」理由。

    sample_descriptions: 用户的 star 仓库 description 抽样(最多 30 条)
    """
    llm = resolve_llm()
    if llm is None:
        raise LLMProviderError(
            "no LLM configured — set provider + api_key in /settings or .env"
        )

    samples = "\n".join(
        f"[{i + 1}] {d}" for i, d in enumerate(sample_descriptions[:30])
    ) or "(no samples)"

    user_prompt = _RATIONALE_USER_TEMPLATE.format(
        term=term, n_stars=n_stars, samples=samples,
    )
    raw = _call_chat(llm, _RATIONALE_SYSTEM, user_prompt, timeout=timeout, max_tokens=200)
    rationale = _clean_text(raw)
    if not rationale:
        raise LLMProviderError("LLM returned empty rationale")
    return rationale


def available_models() -> list[dict]:
    """列出所有 provider + default model(前端 /settings 拉一次显示)。"""
    out = []
    for p, spec in PROVIDERS.items():
        out.append({
            "provider": p.value,
            "default_model": spec.default_model,
            "base_url": spec.base_url,
            "protocol": spec.protocol,
        })
    return out