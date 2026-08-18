# Spec — T007 keywords/llm_upgrade.py

| 维度 | 内容 |
|---|---|
| **TODO ID** | T007（docs/TODO.md §业务核心） |
| **作者** | ai-github-radar 维护者 + AI 助手（2026-08-18） |
| **优先级** | 中 — 默认 TF-IDF 已可用,LLM 是质量升级 |
| **触发** | docs/TODO.md T007 + 用户扩展「LLM 两种格式都要支持,含国产模型」 |

---

## B1. 设计

### 1.1 目标

实现 `src/ai_github_radar/keywords/llm_upgrade.py`,**多 provider 抽象**:

| Provider | 协议 | 默认 base_url | 默认模型 |
|---|---|---|---|
| **openai** | OpenAI Chat Completions | `https://api.openai.com/v1` | `gpt-4o-mini` |
| **anthropic** | Anthropic Messages API | `https://api.anthropic.com` | `claude-3-5-haiku-20241022` |
| **deepseek** | OpenAI 兼容 | `https://api.deepseek.com/v1` | `deepseek-chat` |
| **qwen** (通义千问 DashScope OpenAI 兼容模式) | OpenAI 兼容 | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-turbo` |
| **moonshot** (Kimi) | OpenAI 兼容 | `https://api.moonshot.cn/v1` | `moonshot-v1-8k` |
| **zhipu** (智谱 GLM) | OpenAI 兼容 | `https://open.bigmodel.cn/api/paas/v4/` | `glm-4-flash` |

### 1.2 抽象原则

**OpenAI 兼容协议占主流**（DeepSeek / Qwen / Moonshot / Zhipu 全支持）,**Anthropic 单独走 Messages API**（不兼容）。统一抽象:

```python
class LLMProvider(str, Enum):
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
    protocol: Literal["openai", "anthropic"]  # API 协议族
    env_key: str                              # 默认从哪个 env 读 api key

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
```

### 1.3 主 API

```python
def extract_keywords_via_llm(
    docs: list[str],                         # star 描述+topics+language 拼成
    *,
    provider: str | LLMProvider = "auto",    # "auto" → 从 env 自动探测
    model: str | None = None,                # None → 用 provider 默认 model
    max_keywords: int = 30,
    api_key: str | None = None,              # None → 从 env 读
    base_url: str | None = None,             # None → 用 provider 默认
    timeout: float = 30.0,
) -> list[tuple[str, float]]:
    """LLM 提关键字,返回 [(term, weight 0-10)] 按 weight 降序。

    实现:
      - 拼 prompt: "以下是 N 个 GitHub 仓库描述...请提取 M 个高频技术关键词
        并按相关度打分 1-10,JSON 数组返回"
      - 调 provider API,parse JSON 响应
      - 重试一次(指数退避 1s)
    """

def detect_provider() -> LLMProvider | None:
    """从 env 按优先级探测:OPENAI > ANTHROPIC > DEEPSEEK > QWEN > MOONSHOT > ZHIPU。
    返回第一个找到 key 的 provider,None 表示都没配。
    """
```

### 1.4 配置集成 (T002 config.py 扩展)

settings.llm_provider: str = "auto"     # 用户显式指定
settings.llm_model: str | None = None    # 覆盖默认模型
settings.llm_api_key: SecretStr | None = None  # 覆盖 env 探测(可选)

新增 Provider 环境变量(都不强制,探测用):
- DEEPSEEK_API_KEY / DASHSCOPE_API_KEY / MOONSHOT_API_KEY / ZHIPUAI_API_KEY

### 1.5 非目标

- ❌ Provider 路由(round-robin / fallback) — 用户自选 provider,失败报错不切其他
- ❌ 流式输出(只同步一次拿 JSON)
- ❌ 缓存(阶段二 T201)
- ❌ Function calling / tools

---

## B2. 验收

| AC | 断言 | 怎么验 |
|---|---|---|
| AC-1 | 6 个 provider 全部在 PROVIDERS 注册,字段完整 | 单测:PROVIDERS 长度 == 6,每个有 base_url/default_model/protocol/env_key |
| AC-2 | OpenAI 兼容协议 provider(deepseek/qwen/moonshot/zhipu/openai)走 `chat.completions.create` | 单测:patch OpenAI client,验证调用路径 |
| AC-3 | Anthropic 走 `messages.create` | 单测:patch Anthropic client |
| AC-4 | prompt 提到 max_keywords 数 | 单测:str(docs) + max_keywords=20 在 prompt 里能找到 "20" |
| AC-5 | 响应解析支持 JSON 数组(`[{"term":"x","score":8}]`) | 单测 |
| AC-6 | 响应解析支持 fallback JSON 对象(`{"keywords":[...]}`) | 单测 |
| AC-7 | 失败重试 1 次 | 单测:第一次失败,第二次成功 |
| AC-8 | `detect_provider()` 按优先级返 env 找到的第一个 | 单测:设 DEEPSEEK_API_KEY → 返 DEEPSEEK(比 ANTHROPIC 优先) |
| AC-9 | 无任何 key 时 detect_provider() 返 None | 单测:清空所有 env → None |
| AC-10 | user-override:`api_key` 参数覆盖 env | 单测 |
| AC-11 | user-override:`base_url` 参数覆盖 provider 默认 | 单测:自定义 URL → 验证 client 用自定义 URL |

---

## B3. 测试矩阵

| C | 维度 | 覆盖 |
|---|---|---|
| C1 配置 | 6 provider 注册 | AC-1 |
| C2 功能 | openai 兼容调用 | AC-2 |
| C3 功能 | anthropic 协议 | AC-3 |
| C4 边界 | prompt 含 max_keywords | AC-4 |
| C5 边界 | JSON 数组响应 | AC-5 |
| C6 边界 | JSON 对象响应 | AC-6 |
| C7 错误 | 重试 | AC-7 |
| C8 探测 | env 优先级 | AC-8 |
| C9 探测 | 无 key 返 None | AC-9 |
| C10 用户 | 覆盖 env / base_url | AC-10 / AC-11 |
| C11 一致性 | 返回 list[(term, weight)] 顺序与 T006 extractor 一致(weight 降序) | 单测 |
| C12 错误 | 401/403 → 抛 LLMProviderError | 单测 |

测试文件:`tests/unit/keywords/test_llm_upgrade.py`(mock OpenAI / Anthropic client,不实发请求)

---

## B4. 风险

- **R1**：OpenAI SDK 在 py3.9 装 openai>=1.40,pyproject 已声明。**缓解**：依赖装齐。
- **R2**：Anthropic SDK 协议偶尔升级。**缓解**:用 anthropic SDK 的 messages API(稳定)。
- **R3**：国产 provider 的 OpenAI 兼容实现偶有差异(如 Qwen 不支持 `temperature=0` 某些模型)。**缓解**:留 `temperature=0.3` 默认值,出错抛 LLMProviderError 让用户改。
- **R4**：prompt 注入风险(描述里可能含恶意指令)。**缓解**:prompt 强约束"只输出 JSON 数组",系统消息明示。
- **R5**：LLM 响应可能不带合法 JSON(模型"忘记"格式)。**缓解**:先用 `json.loads` parse,失败尝试正则提取 `[{...}]`,再失败抛错。