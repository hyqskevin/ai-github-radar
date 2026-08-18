"""LLM 关键字升级 — T007 多 provider.

支持 OpenAI 兼容协议(OpenAI / DeepSeek / Qwen / Moonshot / Zhipu)
+ Anthropic Messages API(anthropic)。

默认走 TF-IDF(T006),用户配 env key 后 init 自动升级。
"""

from __future__ import annotations

import enum
import json
import logging
import os
import re
import time
from dataclasses import dataclass
from typing import Callable, Literal, Optional, Union

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Provider 注册
# ---------------------------------------------------------------------------


class LLMProvider(str, enum.Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    DEEPSEEK = "deepseek"
    QWEN = "qwen"
    MOONSHOT = "moonshot"
    ZHIPU = "zhipu"


@dataclass(frozen=True)
class ProviderSpec:
    base_url: str
    default_model: str
    protocol: Literal["openai", "anthropic"]
    env_key: str


PROVIDERS: dict[LLMProvider, ProviderSpec] = {
    LLMProvider.OPENAI: ProviderSpec(
        base_url="https://api.openai.com/v1",
        default_model="gpt-4o-mini",
        protocol="openai",
        env_key="OPENAI_API_KEY",
    ),
    LLMProvider.ANTHROPIC: ProviderSpec(
        base_url="https://api.anthropic.com",
        default_model="claude-3-5-haiku-20241022",
        protocol="anthropic",
        env_key="ANTHROPIC_API_KEY",
    ),
    LLMProvider.DEEPSEEK: ProviderSpec(
        base_url="https://api.deepseek.com/v1",
        default_model="deepseek-chat",
        protocol="openai",
        env_key="DEEPSEEK_API_KEY",
    ),
    LLMProvider.QWEN: ProviderSpec(
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        default_model="qwen-turbo",
        protocol="openai",
        env_key="DASHSCOPE_API_KEY",
    ),
    LLMProvider.MOONSHOT: ProviderSpec(
        base_url="https://api.moonshot.cn/v1",
        default_model="moonshot-v1-8k",
        protocol="openai",
        env_key="MOONSHOT_API_KEY",
    ),
    LLMProvider.ZHIPU: ProviderSpec(
        base_url="https://open.bigmodel.cn/api/paas/v4/",
        default_model="glm-4-flash",
        protocol="openai",
        env_key="ZHIPUAI_API_KEY",
    ),
}

# env 探测优先级(OpenAI 最先,国际优先)
_DETECT_ORDER: tuple[LLMProvider, ...] = (
    LLMProvider.OPENAI,
    LLMProvider.ANTHROPIC,
    LLMProvider.DEEPSEEK,
    LLMProvider.QWEN,
    LLMProvider.MOONSHOT,
    LLMProvider.ZHIPU,
)


class LLMProviderError(Exception):
    """LLM provider 调用失败(网络 / 401 / 解析失败 / 无 key)。"""


# ---------------------------------------------------------------------------
# Provider 探测
# ---------------------------------------------------------------------------


def detect_provider() -> Optional[LLMProvider]:
    """从 env 按 _DETECT_ORDER 优先级找第一个有 key 的 provider。"""
    for p in _DETECT_ORDER:
        env_key = PROVIDERS[p].env_key
        if os.environ.get(env_key):
            return p
    return None


# ---------------------------------------------------------------------------
# 主 API
# ---------------------------------------------------------------------------


def extract_keywords_via_llm(
    docs: list[str],
    *,
    provider: Union[str, LLMProvider] = "auto",
    model: Optional[str] = None,
    max_keywords: int = 30,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    timeout: float = 30.0,
    _retry_sleep: Callable[[float], None] = time.sleep,
) -> list[tuple[str, float]]:
    """LLM 提关键字,返回 list[(term, weight)] 按 weight 降序。"""
    if not docs:
        return []
    if max_keywords < 1:
        raise ValueError(f"max_keywords must be >= 1, got {max_keywords}")

    # 解析 provider
    if isinstance(provider, str):
        if provider == "auto":
            p = detect_provider()
            if p is None:
                raise LLMProviderError(
                    "provider='auto' but no LLM API key found in env "
                    f"(checked: {', '.join(PROVIDERS[x].env_key for x in _DETECT_ORDER)})"
                )
        else:
            try:
                p = LLMProvider(provider)
            except ValueError as e:
                raise ValueError(
                    f"unknown provider {provider!r}; "
                    f"valid: {[x.value for x in LLMProvider]}"
                ) from e
    else:
        p = provider

    spec = PROVIDERS[p]

    # 解析 api_key
    if api_key is None:
        api_key = os.environ.get(spec.env_key)
    if not api_key:
        raise LLMProviderError(
            f"provider {p.value!r} requires {spec.env_key} env var or api_key= arg"
        )

    # 解析 model
    use_model = model or spec.default_model

    # 解析 base_url
    use_base_url = base_url or spec.base_url

    # 拼 prompt
    user_prompt = _build_prompt(docs, max_keywords)

    # 调用
    if spec.protocol == "openai":
        text = _call_openai_compat(
            api_key=api_key,
            base_url=use_base_url,
            model=use_model,
            user_prompt=user_prompt,
            timeout=timeout,
            retry_sleep=_retry_sleep,
        )
    else:  # anthropic
        text = _call_anthropic(
            api_key=api_key,
            base_url=use_base_url,
            model=use_model,
            user_prompt=user_prompt,
            timeout=timeout,
            retry_sleep=_retry_sleep,
        )

    return _parse_keywords_response(text, max_keywords)


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------


_PROMPT_TEMPLATE = """你是一位 GitHub 项目技术趋势分析专家。下面是用户 star 过的 {n_docs} 个 GitHub 仓库的描述+主题+语言信息。

请提取其中最高频、最具区分度的技术关键词 {max_keywords} 个,并按相关度打分(1-10,10 分最强)。

严格要求:
1. 只输出 JSON 数组,不要任何解释或 markdown 代码块
2. 每项格式: {{"term": "<关键词,1-3 个词>", "score": <1-10 整数>}}
3. 关键词要小写、去停用词;允许 bigram 如 "machine learning"
4. 优先提取**技术栈信号**(框架 / 语言特性 / 协议 / 范式),不提取"awesome" "library" 这种通用词
5. 按 score 降序排列

仓库信息(每个一组):
---
{docs}
"""


def _build_prompt(docs: list[str], max_keywords: int) -> str:
    """拼 user prompt(系统消息固定为「你是技术趋势分析专家」)。"""
    # 文档列表形式呈现,每条 doc 单行
    docs_text = "\n".join(f"[{i + 1}] {d}" for i, d in enumerate(docs))
    return _PROMPT_TEMPLATE.format(
        n_docs=len(docs), max_keywords=max_keywords, docs=docs_text
    )


_SYSTEM_PROMPT = (
    "你是一位 GitHub 项目技术趋势分析专家,"
    "擅长从仓库元数据中提取高频技术关键词并按相关度打分。"
)


# ---------------------------------------------------------------------------
# OpenAI 兼容协议
# ---------------------------------------------------------------------------


def _get_openai_client(api_key: str, base_url: str, timeout: float):
    """构造 OpenAI 同步 client。测试可 patch。"""
    import openai

    return openai.OpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=timeout,
    )


def _call_openai_compat(
    *,
    api_key: str,
    base_url: str,
    model: str,
    user_prompt: str,
    timeout: float,
    retry_sleep: Callable[[float], None],
) -> str:
    """OpenAI 兼容协议(OpenAI / DeepSeek / Qwen / Moonshot / Zhipu)。"""
    client = _get_openai_client(api_key, base_url, timeout)
    last_err: Optional[Exception] = None
    for attempt in range(2):  # 1 initial + 1 retry
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
            )
            return resp.choices[0].message.content or ""
        except Exception as e:
            last_err = e
            log.warning("LLM call attempt %d failed: %s", attempt + 1, e)
            if attempt == 0:
                retry_sleep(1.0)
    raise LLMProviderError(
        f"OpenAI-compat call failed after 2 attempts: {last_err}"
    ) from last_err


# ---------------------------------------------------------------------------
# Anthropic 协议
# ---------------------------------------------------------------------------


def _get_anthropic_client(api_key: str, base_url: str, timeout: float):
    import anthropic

    return anthropic.Anthropic(
        api_key=api_key,
        base_url=base_url,
        timeout=timeout,
    )


def _call_anthropic(
    *,
    api_key: str,
    base_url: str,
    model: str,
    user_prompt: str,
    timeout: float,
    retry_sleep: Callable[[float], None],
) -> str:
    client = _get_anthropic_client(api_key, base_url, timeout)
    last_err: Optional[Exception] = None
    for attempt in range(2):
        try:
            resp = client.messages.create(
                model=model,
                max_tokens=2048,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
                temperature=0.3,
            )
            # content 是 list[TextBlock | ...]
            if resp.content:
                return resp.content[0].text
            return ""
        except Exception as e:
            last_err = e
            log.warning("Anthropic call attempt %d failed: %s", attempt + 1, e)
            if attempt == 0:
                retry_sleep(1.0)
    raise LLMProviderError(
        f"Anthropic call failed after 2 attempts: {last_err}"
    ) from last_err


# ---------------------------------------------------------------------------
# 响应解析
# ---------------------------------------------------------------------------


_JSON_ARRAY_RE = re.compile(r"\[\s*\{[\s\S]*?\}\s*\]")


def _parse_keywords_response(text: str, max_keywords: int) -> list[tuple[str, float]]:
    """解析 LLM 响应,支持 JSON 数组 / JSON 对象 / 文本中夹带 JSON。"""
    if not text or not text.strip():
        raise LLMProviderError("LLM returned empty response")

    # 直接 json.loads 尝试
    payload = None
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        # 尝试从文本里抽 JSON 数组
        m = _JSON_ARRAY_RE.search(text)
        if m:
            try:
                payload = json.loads(m.group(0))
            except json.JSONDecodeError:
                pass

    if payload is None:
        raise LLMProviderError(
            f"LLM response not parseable as keyword array: {text[:200]!r}"
        )

    # 兼容 list 和 dict
    if isinstance(payload, dict):
        items = payload.get("keywords") or payload.get("data") or []
    elif isinstance(payload, list):
        items = payload
    else:
        raise LLMProviderError(f"unexpected LLM response type: {type(payload).__name__}")

    out: list[tuple[str, float]] = []
    for item in items[:max_keywords]:
        if not isinstance(item, dict):
            continue
        term = item.get("term") or item.get("keyword") or item.get("name")
        score = item.get("score") or item.get("weight") or item.get("relevance")
        if term is None or score is None:
            continue
        try:
            score_f = float(score)
        except (TypeError, ValueError):
            continue
        # 归一化到 0-10
        score_f = max(0.0, min(score_f, 10.0))
        out.append((str(term).strip().lower(), score_f))
    if not out:
        raise LLMProviderError("LLM response parsed but no valid keywords found")
    # 按 weight 降序稳定排序
    out.sort(key=lambda x: (-x[1], x[0]))
    return out