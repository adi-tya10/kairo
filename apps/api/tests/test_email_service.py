"""
Unit and Integration Tests for EmailService & Invitation Dispatch.
"""

from unittest.mock import MagicMock, patch

import pytest

from apps.api.app.core.config import get_settings
from apps.api.app.services.email_service import EmailService


def test_build_invitation_html_with_team():
    html = EmailService._build_invitation_html(
        recipient_name="Rahul Sharma",
        organization_name="Snapmeet",
        team_name="Billing Pod",
        role="DEVELOPER",
        invite_url="https://kairo-web.onrender.com/auth?invite=token123",
        base_url="https://kairo-web.onrender.com",
    )
    assert "Rahul Sharma" in html
    assert "Snapmeet" in html
    assert "Billing Pod" in html
    assert "DEVELOPER" in html
    assert "https://kairo-web.onrender.com/auth?invite=token123" in html
    assert "raw.githubusercontent.com/adi-tya10/kairo/main/apps/web/public/kairo.png" in html
    assert "localhost" not in html


def test_build_invitation_html_without_team_and_name():
    html = EmailService._build_invitation_html(
        recipient_name=None,
        organization_name="Acme",
        team_name=None,
        role="ADMIN",
        invite_url="https://kairo-web.onrender.com/auth?invite=token456",
        base_url="https://kairo-web.onrender.com",
    )
    assert "Hi <strong style=\"color: #F8FAFC;\">there</strong>" in html
    assert "Acme" in html
    assert "ADMIN" in html
    assert "raw.githubusercontent.com/adi-tya10/kairo/main/apps/web/public/kairo.png" in html
    assert "localhost" not in html


def test_build_invitation_text():
    text = EmailService._build_invitation_text(
        recipient_name="Aman",
        organization_name="Snapmeet",
        team_name="Core",
        role="LEAD",
        invite_url="http://localhost:3000/auth?invite=token789",
    )
    assert "Hi Aman" in text
    assert "Team: Core" in text
    assert "http://localhost:3000/auth?invite=token789" in text


def test_send_smtp_sync_unconfigured():
    settings = get_settings()
    with (
        patch.object(settings, "SMTP_USER", ""),
        patch.object(settings, "SMTP_PASSWORD", ""),
    ):
        result = EmailService._send_smtp_sync(
            to_email="test@example.com",
            subject="Test Subject",
            html_body="<p>Test</p>",
            text_body="Test",
        )
        assert result is False


def test_send_smtp_sync_success():
    settings = get_settings()
    with (
        patch.object(settings, "SMTP_USER", "mock_user"),
        patch.object(settings, "SMTP_PASSWORD", "mock_pass"),
        patch("smtplib.SMTP") as mock_smtp_class,
    ):
        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_server

        result = EmailService._send_smtp_sync(
            to_email="developer@example.com",
            subject="Welcome to KAIRO",
            html_body="<p>HTML</p>",
            text_body="TEXT",
        )
        assert result is True
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("mock_user", "mock_pass")
        mock_server.sendmail.assert_called_once()


def test_send_smtp_sync_connection_failure():
    settings = get_settings()
    with (
        patch.object(settings, "SMTP_USER", "mock_user"),
        patch.object(settings, "SMTP_PASSWORD", "mock_pass"),
        patch("smtplib.SMTP", side_effect=ConnectionError("SMTP server unreachable")),
    ):
        result = EmailService._send_smtp_sync(
            to_email="developer@example.com",
            subject="Welcome",
            html_body="<p>HTML</p>",
            text_body="TEXT",
        )
        assert result is False


@pytest.mark.asyncio
async def test_send_invitation_email_async():
    with patch.object(EmailService, "_send_smtp_sync", return_value=True) as mock_sync:
        success = await EmailService.send_invitation_email(
            to_email="new_dev@company.com",
            recipient_name="Priya",
            organization_id="snapmeet",
            team_name="Payments",
            role="DEVELOPER",
            invite_token="token_abc",
        )
        assert success is True
        mock_sync.assert_called_once()
