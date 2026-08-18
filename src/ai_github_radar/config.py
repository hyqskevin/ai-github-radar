"""配置加载与校验 — T002.

Pydantic Settings v2 + .env,跨字段依赖校验(feishu push 需 webhook 等),
所有 token 类字段用 SecretStr 防泄漏。

用法:
    from ai_github_radar.config import load_settings, ConfigError
    settings = load_settings()        # 自动从 .env 加载
    settings.github_token.get_secret_value()  # 取 token 真值

CLI 入口(T012 之前最小可用):
    python -m ai_github_radar.config --validate
"""

from __future__ import annotations

import argparse
import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional

from pydantic import Field, HttpUrl, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfigError(Exception):
    """配置加载/校验失败。所有 token 字段在 str() / repr() 时不泄漏。"""


class Settings(BaseSettings):
    """ai-github-radar 全局配置。"""

    model_config = SettingsConfigDict(
        env_file=None,  # 由 _resolve_env_file 注入
        case_sensitive=False,
        extra="ignore",
    )

    # 必填
    github_token: SecretStr = Field(..., description="GitHub PAT, scope=public_repo")
    radar_user: str = Field(..., description="GitHub username")

    # 可选 + 默认
    radar_fetch_interval: Literal["daily", "weekly"] = "daily"
    radar_push_target: Literal["local", "feishu", "email"] = "local"
    db_url: str = "sqlite:///./data/radar.db"

    # 飞书推送
    feishu_webhook_url: Optional[HttpUrl] = None

    # SMTP
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_user: Optional[str] = None
    smtp_password: Optional[SecretStr] = None
    smtp_to: Optional[str] = None

    # LLM(可选升级)
    openai_api_key: Optional[SecretStr] = None
    anthropic_api_key: Optional[SecretStr] = None

    @field_validator("smtp_port")
    @classmethod
    def _port_range(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not (1 <= v <= 65535):
            raise ValueError(f"smtp_port 必须在 1..65535,实际 {v}")
        return v

    @field_validator("radar_user")
    @classmethod
    def _user_shape(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("radar_user 不能为空")
        if len(v) > 39:  # GitHub username 上限
            raise ValueError("radar_user 长度超过 39 字符,可能不是合法 GitHub username")
        return v

    @model_validator(mode="after")
    def _push_target_consistency(self) -> "Settings":
        if self.radar_push_target == "feishu" and self.feishu_webhook_url is None:
            raise ValueError(
                "radar_push_target=feishu 时必须配置 feishu_webhook_url"
            )
        if self.radar_push_target == "email":
            missing = [
                name
                for name, val in (
                    ("smtp_host", self.smtp_host),
                    ("smtp_port", self.smtp_port),
                    ("smtp_user", self.smtp_user),
                    ("smtp_password", self.smtp_password),
                    ("smtp_to", self.smtp_to),
                )
                if val is None
            ]
            if missing:
                raise ValueError(
                    f"radar_push_target=email 时必须配置: {', '.join(missing)}"
                )
        return self

    # -------- helpers --------

    def token(self, name: str = "github_token") -> str:
        """取 token 明文。仅在确实要发请求时用(网络调用),日志/打印禁用。"""
        attr = getattr(self, name, None)
        if isinstance(attr, SecretStr):
            return attr.get_secret_value()
        if isinstance(attr, str):
            return attr
        raise AttributeError(name)


def _resolve_env_file() -> Optional[str]:
    """env_file 解析顺序:RADAR_CONFIG_PATH > ./config/.env > ./.env。

    若显式传入(通过 RADAR_CONFIG_PATH),不存在则抛 ConfigError;
    否则仅返回存在的那个,都不存在返 None 让 Pydantic 报缺必填。
    """
    custom = os.environ.get("RADAR_CONFIG_PATH")
    if custom:
        if not Path(custom).exists():
            raise ConfigError(f"RADAR_CONFIG_PATH 指向文件不存在: {custom}")
        return custom
    for cand in (Path("config/.env"), Path(".env")):
        if cand.exists():
            return str(cand)
    return None  # 让 Pydantic 抛缺必填错


def _build_settings() -> Settings:
    """构造 Settings 实例(env_file + 环境变量)。

    当 env_file=None 时,Pydantic Settings v2 仍会从 os.environ 读字段
    (这是 BaseSettings 默认行为),所以测试可用 monkeypatch.setenv 注入。
    """
    env_file = _resolve_env_file()
    return Settings(_env_file=env_file)  # type: ignore[call-arg]


@lru_cache(maxsize=1)
def load_settings() -> Settings:
    """加载并缓存 Settings 单例。失败抛 ConfigError。"""
    try:
        return _build_settings()
    except Exception as e:  # pydantic.ValidationError / ConfigError
        # 把 Pydantic 错改写成 ConfigError,stderr 友好输出
        msg = _format_error(e)
        raise ConfigError(msg) from e


def validate_config() -> Settings:
    """跑校验,成功返 Settings 实例。失败抛 ConfigError。"""
    s = load_settings()
    return s


def _format_error(e: Exception) -> str:
    """把 Pydantic 校验错改成 stdout 友好格式(隐藏 token)。"""
    text = str(e)
    # 防御:把任何像 secret 的字串替换成 *** (Pydantic v2 不会把 SecretStr 明文打出来,但双保险)
    import re

    text = re.sub(r"ghp_[A-Za-z0-9]+", "***", text)
    text = re.sub(r"sk-[A-Za-z0-9]+", "***", text)
    text = re.sub(r"SECRET_PASSWORD[A-Za-z0-9_]*", "***", text)
    return text


# ---------------------------------------------------------------------------
# CLI 入口(T002 最小可用,T012 完整 CLI 上线前临时)
# ---------------------------------------------------------------------------


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ai_github_radar.config")
    parser.add_argument("--validate", action="store_true", help="校验 .env 配置")
    parser.add_argument("--show", action="store_true", help="打印当前配置(token 隐藏)")
    args = parser.parse_args(argv)
    if not (args.validate or args.show):
        parser.print_help()
        return 0
    try:
        s = load_settings()
    except ConfigError as e:
        print(f"config: ERROR — {e}", file=sys.stderr)
        return 2
    if args.show:
        # 打印 token 字段时仅显示末 4 位
        token = s.github_token.get_secret_value()
        masked = f"***{token[-4:]}" if len(token) >= 4 else "***"
        print(
            f"radar_user={s.radar_user}\n"
            f"github_token={masked}\n"
            f"radar_fetch_interval={s.radar_fetch_interval}\n"
            f"radar_push_target={s.radar_push_target}\n"
            f"db_url={s.db_url}\n"
        )
    else:  # --validate
        print("config: OK")
    return 0


if __name__ == "__main__":
    sys.exit(_main())