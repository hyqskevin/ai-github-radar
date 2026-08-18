"""T011 push/email.py 测试。"""

from __future__ import annotations

import smtplib
from email import message_from_string
from unittest.mock import MagicMock, patch

import pytest

from ai_github_radar.push.email import (
    EmailPushError,
    push_email,
    render_html_email,
    render_text_email,
)


SAMPLE_RECS = [
    {
        "repo_id": 100, "full_name": "owner1/repo1",
        "description": "Python FastAPI web framework",
        "language": "Python", "score": 12.34,
        "matched_keywords": ["fastapi", "async"], "rank": 1, "stars_today": 200,
    },
    {
        "repo_id": 200, "full_name": "owner2/repo2",
        "description": "Rust async runtime",
        "language": "Rust", "score": 9.5,
        "matched_keywords": ["async"], "rank": 2, "stars_today": 80,
    },
]


# ---------------------------------------------------------------------------
# render_html_email
# ---------------------------------------------------------------------------


def test_ac1_html_contains_html_tag_and_inline_css() -> None:
    """AC-1: HTML 含 <html> + 内联 CSS。"""
    out = render_html_email(SAMPLE_RECS, date="2026-08-19")
    assert "<html" in out
    assert "style=" in out  # 内联 CSS


def test_ac2_recs_full_name_and_score_rendered() -> None:
    """AC-2: full_name / description / score 进 HTML。"""
    out = render_html_email(SAMPLE_RECS, date="2026-08-19")
    assert "owner1/repo1" in out
    assert "Python FastAPI web framework" in out
    assert "12.34" in out or "12.340" in out


def test_ac3_language_emoji_in_html() -> None:
    """AC-3: language emoji (T009 复用) 在 HTML 中。"""
    out = render_html_email(SAMPLE_RECS, date="2026-08-19")
    assert "🐍" in out
    assert "🦀" in out


def test_html_escapes_user_input() -> None:
    """HTML 转义:用户输入 < > & 不会破坏 HTML。"""
    recs = [{
        "repo_id": 1, "full_name": "evil/repo",
        "description": "<script>alert('xss')</script>",
        "language": "Python", "score": 5.0,
        "matched_keywords": [], "rank": 1, "stars_today": 10,
    }]
    out = render_html_email(recs, date="2026-08-19")
    assert "<script>alert" not in out
    assert "&lt;script&gt;" in out


# ---------------------------------------------------------------------------
# render_text_email
# ---------------------------------------------------------------------------


def test_ac4_text_is_plain() -> None:
    """AC-4: 纯文本,无 HTML 标签。"""
    out = render_text_email(SAMPLE_RECS, date="2026-08-19")
    assert "<" not in out
    assert ">" not in out
    assert "owner1/repo1" in out


# ---------------------------------------------------------------------------
# push_email — SMTP 路径
# ---------------------------------------------------------------------------


def _make_smtp_mock():
    """构造 mock smtplib.SMTP 实例。

    不带 spec(spec=SMTP class 会要求 connect/quit 等 method 真实存在)。
    """
    instance = MagicMock()
    return instance


@patch("ai_github_radar.push.email.smtplib.SMTP")
def test_ac5_smtp_connect_login_sendmail(mock_smtp_cls: MagicMock) -> None:
    """AC-5: push_email 走 connect + login + sendmail。"""
    mock_inst = _make_smtp_mock()
    mock_smtp_cls.return_value = mock_inst

    push_email(
        SAMPLE_RECS,
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_user="user@example.com",
        smtp_password="secret",
        smtp_to="alice@example.com",
    )
    mock_smtp_cls.assert_called_once()
    mock_inst.connect.assert_called_once()
    mock_inst.login.assert_called_once()
    mock_inst.sendmail.assert_called_once()


@patch("ai_github_radar.push.email.smtplib.SMTP")
def test_ac6_with_password_calls_login(mock_smtp_cls: MagicMock) -> None:
    """AC-6: smtp_password 提供 → login 被调。"""
    mock_inst = _make_smtp_mock()
    mock_smtp_cls.return_value = mock_inst
    push_email(SAMPLE_RECS, smtp_host="h", smtp_port=587,
                smtp_user="u", smtp_password="p",
                smtp_to="a@b.c")
    assert mock_inst.login.called


@patch("ai_github_radar.push.email.smtplib.SMTP")
def test_ac7_without_password_skips_login(mock_smtp_cls: MagicMock) -> None:
    """AC-7: smtp_password=None → 不 login(匿名 SMTP)。"""
    mock_inst = _make_smtp_mock()
    mock_smtp_cls.return_value = mock_inst
    push_email(SAMPLE_RECS, smtp_host="h", smtp_port=587,
                smtp_user=None, smtp_password=None,
                smtp_to="a@b.c")
    assert not mock_inst.login.called


@patch("ai_github_radar.push.email.smtplib.SMTP")
def test_ac8_use_tls_calls_starttls(mock_smtp_cls: MagicMock) -> None:
    """AC-8: use_tls=True → starttls 被调。"""
    mock_inst = _make_smtp_mock()
    mock_smtp_cls.return_value = mock_inst
    push_email(SAMPLE_RECS, smtp_host="h", smtp_port=587,
                smtp_to="a@b.c", use_tls=True)
    assert mock_inst.starttls.called


@patch("ai_github_radar.push.email.smtplib.SMTP")
def test_ac8_use_tls_false_skips_starttls(mock_smtp_cls: MagicMock) -> None:
    """use_tls=False → 不 starttls。"""
    mock_inst = _make_smtp_mock()
    mock_smtp_cls.return_value = mock_inst
    push_email(SAMPLE_RECS, smtp_host="h", smtp_port=25,
                smtp_to="a@b.c", use_tls=False)
    assert not mock_inst.starttls.called


@patch("ai_github_radar.push.email.smtplib.SMTP")
def test_ac9_smtp_to_string_normalized_to_list(mock_smtp_cls: MagicMock) -> None:
    """AC-9: smtp_to 是 str → list 化。"""
    mock_inst = _make_smtp_mock()
    mock_smtp_cls.return_value = mock_inst
    push_email(SAMPLE_RECS, smtp_host="h", smtp_port=587, smtp_to="a@b.c")
    call_args = mock_inst.sendmail.call_args
    # sendmail(from_addr, to_addrs, msg),to_addrs 应是 list
    assert isinstance(call_args.args[1], list)
    assert "a@b.c" in call_args.args[1]


@patch("ai_github_radar.push.email.smtplib.SMTP")
def test_ac9_smtp_to_list_passes_through(mock_smtp_cls: MagicMock) -> None:
    """smtp_to 是 list → 直接用。"""
    mock_inst = _make_smtp_mock()
    mock_smtp_cls.return_value = mock_inst
    push_email(SAMPLE_RECS, smtp_host="h", smtp_port=587,
                smtp_to=["a@b.c", "d@e.f"])
    call_args = mock_inst.sendmail.call_args
    assert call_args.args[1] == ["a@b.c", "d@e.f"]


@patch("ai_github_radar.push.email.smtplib.SMTP")
def test_ac10_smtp_exception_raises_email_error(mock_smtp_cls: MagicMock) -> None:
    """AC-10: SMTP 异常 → EmailPushError。"""
    mock_inst = _make_smtp_mock()
    mock_inst.connect.side_effect = smtplib.SMTPException("connection refused")
    mock_smtp_cls.return_value = mock_inst
    with pytest.raises(EmailPushError):
        push_email(SAMPLE_RECS, smtp_host="h", smtp_port=587, smtp_to="a@b.c")


@patch("ai_github_radar.push.email.smtplib.SMTP")
def test_ac11_returns_dict_with_metadata(mock_smtp_cls: MagicMock) -> None:
    """AC-11: 返回 dict 含 to / subject / sent_at。"""
    mock_inst = _make_smtp_mock()
    mock_smtp_cls.return_value = mock_inst
    result = push_email(
        SAMPLE_RECS, smtp_host="h", smtp_port=587,
        smtp_to=["a@b.c"], subject_prefix="[Test]",
    )
    assert "to" in result
    assert "subject" in result
    assert "sent_at" in result
    assert result["to"] == ["a@b.c"]
    assert "[Test]" in result["subject"]


@patch("ai_github_radar.push.email.smtplib.SMTP")
def test_ac12_multipart_alternative(mock_smtp_cls: MagicMock) -> None:
    """AC-12: multipart/alternative 含 text/plain + text/html。"""
    mock_inst = _make_smtp_mock()
    mock_smtp_cls.return_value = mock_inst
    push_email(SAMPLE_RECS, smtp_host="h", smtp_port=587, smtp_to="a@b.c")
    raw_msg = mock_inst.sendmail.call_args.args[2]
    # parse 邮件
    msg = message_from_string(raw_msg)
    # 是 multipart
    assert msg.is_multipart()
    # 含 text/plain + text/html
    types = [p.get_content_type() for p in msg.walk()]
    assert "text/plain" in types
    assert "text/html" in types


@patch("ai_github_radar.push.email.smtplib.SMTP")
def test_sendmail_called_with_from(mock_smtp_cls: MagicMock) -> None:
    """sendmail 第 1 个参数是 from 地址(smtp_user 优先,空则 default)。"""
    mock_inst = _make_smtp_mock()
    mock_smtp_cls.return_value = mock_inst
    push_email(SAMPLE_RECS, smtp_host="h", smtp_port=587,
                smtp_user="radar@example.com", smtp_to="a@b.c")
    call_args = mock_inst.sendmail.call_args
    assert call_args.args[0] == "radar@example.com"


@patch("ai_github_radar.push.email.smtplib.SMTP")
def test_sendmail_from_falls_back_to_first_recipient(mock_smtp_cls: MagicMock) -> None:
    """smtp_user=None → from 用第一个 smtp_to 地址。"""
    mock_inst = _make_smtp_mock()
    mock_smtp_cls.return_value = mock_inst
    push_email(SAMPLE_RECS, smtp_host="h", smtp_port=587,
                smtp_user=None, smtp_to="alice@example.com")
    call_args = mock_inst.sendmail.call_args
    assert call_args.args[0] == "alice@example.com"


def test_invalid_smtp_to_type_raises() -> None:
    """smtp_to 类型错(int)→ ValueError。"""
    with pytest.raises(ValueError):
        push_email(SAMPLE_RECS, smtp_host="h", smtp_port=587, smtp_to=12345)  # type: ignore[arg-type]