"""
Email Service for KAIRO.

Handles transactional email dispatch (invitations, alerts, security notifications)
via standard SMTP relays (Brevo, Gmail, AWS SES) in a non-blocking asynchronous manner.
"""

import asyncio
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from apps.api.app.core.config import get_settings
from apps.api.app.core.logging import get_logger

logger = get_logger("kairo.services.email")


class EmailService:
    """Enterprise transactional email dispatcher."""

    @classmethod
    def _build_invitation_html(
        cls,
        recipient_name: str | None,
        organization_name: str,
        team_name: str | None,
        role: str,
        invite_url: str,
        base_url: str,
    ) -> str:
        name_display = recipient_name if recipient_name else "there"
        logo_url = "https://raw.githubusercontent.com/adi-tya10/kairo/main/apps/web/public/kairo.png"
        team_row = (
            f"""
            <tr>
              <td style="padding: 8px 0; color: #94A3B8; font-size: 13px;">Assigned Team:</td>
              <td style="padding: 8px 0; color: #F8FAFC; font-size: 13px; font-weight: 600; text-align: right;">{team_name}</td>
            </tr>
            """
            if team_name
            else ""
        )

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Invitation to join {organization_name} on KAIRO</title>
</head>
<body style="margin: 0; padding: 0; background-color: #030712; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #F8FAFC;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #030712; padding: 40px 16px;">
    <tr>
      <td align="center">
        <!-- Main Container -->
        <table role="presentation" width="100%" style="max-width: 560px; background-color: #0F172A; border: 1px solid #1E293B; border-radius: 12px; overflow: hidden; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);">

          <!-- Header Banner with Transparent Logo -->
          <tr>
            <td style="padding: 32px 36px 24px; border-bottom: 1px solid #1E293B; background: linear-gradient(180deg, #1E293B 0%, #0F172A 100%);">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                <tr>
                  <td valign="middle" style="width: 44px;">
                    <a href="{base_url}" target="_blank" style="text-decoration: none;">
                      <img src="{logo_url}" alt="KAIRO Emblem" width="40" height="40" style="display: block; width: 40px; height: 40px; object-fit: contain; border: 0;" />
                    </a>
                  </td>
                  <td valign="middle" style="padding-left: 12px;">
                    <span style="font-size: 18px; font-weight: 800; color: #F8FAFC; letter-spacing: -0.02em; line-height: 1;">KAIRO</span>
                    <div style="display: inline-block; margin-left: 8px; padding: 2px 8px; background: rgba(59, 130, 246, 0.1); border: 1px solid rgba(59, 130, 246, 0.3); border-radius: 4px; color: #60A5FA; font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;">
                      Work Continuity
                    </div>
                  </td>
                </tr>
                <tr>
                  <td colspan="2" style="padding-top: 18px;">
                    <h1 style="margin: 0 0 6px; font-size: 22px; font-weight: 700; color: #F8FAFC; letter-spacing: -0.02em;">
                      You've been invited to join {organization_name}
                    </h1>
                    <p style="margin: 0; font-size: 14px; color: #94A3B8;">
                      Collaborate on code, eliminate context loss, and activate your desktop HUD.
                    </p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Content Body -->
          <tr>
            <td style="padding: 32px 36px;">
              <p style="margin: 0 0 18px; font-size: 15px; line-height: 1.6; color: #E2E8F0;">
                Hi <strong style="color: #F8FAFC;">{name_display}</strong>,
              </p>
              <p style="margin: 0 0 24px; font-size: 14px; line-height: 1.6; color: #94A3B8;">
                You have been invited to join <strong style="color: #F8FAFC;">{organization_name}</strong> on KAIRO. With KAIRO, your in-flight commits, Jira tasks, and architecture decisions are automatically connected without manual status reports.
              </p>

              <!-- Details Box -->
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #0A0F1D; border: 1px solid #1E293B; border-radius: 8px; margin-bottom: 28px; padding: 16px 20px;">
                <tr>
                  <td style="padding: 8px 0; color: #94A3B8; font-size: 13px;">Organization:</td>
                  <td style="padding: 8px 0; color: #F8FAFC; font-size: 13px; font-weight: 600; text-align: right;">{organization_name}</td>
                </tr>
                {team_row}
                <tr>
                  <td style="padding: 8px 0; color: #94A3B8; font-size: 13px;">Assigned Role:</td>
                  <td style="padding: 8px 0; color: #38BDF8; font-size: 13px; font-weight: 600; text-align: right;">{role}</td>
                </tr>
                <tr>
                  <td style="padding: 8px 0; color: #94A3B8; font-size: 13px;">Link Expiration:</td>
                  <td style="padding: 8px 0; color: #F59E0B; font-size: 13px; font-weight: 500; text-align: right;">7 Days</td>
                </tr>
              </table>

              <!-- Action Button -->
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin-bottom: 28px;">
                <tr>
                  <td align="center">
                    <a href="{invite_url}" target="_blank" style="display: inline-block; width: 100%; box-sizing: border-box; text-align: center; background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%); color: #FFFFFF; text-decoration: none; font-size: 14px; font-weight: 600; padding: 14px 24px; border-radius: 8px; box-shadow: 0 4px 14px rgba(37, 99, 235, 0.4);">
                      Accept Invitation &amp; Setup KAIRO HUD &rarr;
                    </a>
                  </td>
                </tr>
              </table>

              <p style="margin: 0 0 12px; font-size: 12px; color: #64748B; line-height: 1.5;">
                After accepting your invitation, you'll be guided to download the KAIRO Desktop Floating HUD (available for Windows, macOS, and Linux) to automatically connect your local git branches with your team pod.
              </p>

              <!-- Fallback Link -->
              <p style="margin: 0; font-size: 11px; color: #475569; word-break: break-all;">
                If the button above doesn't work, copy and paste this link into your browser:<br>
                <a href="{invite_url}" style="color: #60A5FA; text-decoration: underline;">{invite_url}</a>
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding: 20px 36px; border-top: 1px solid #1E293B; background-color: #070B14; text-align: center;">
              <p style="margin: 0 0 6px; font-size: 11px; color: #64748B;">
                Sent securely by <a href="{base_url}" target="_blank" style="color: #60A5FA; text-decoration: none; font-weight: 600;">KAIRO</a> Autonomous Work Continuity Engine
              </p>
              <p style="margin: 0; font-size: 11px; color: #475569;">
                If you were not expecting this invitation, you can safely ignore this email.
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""

    @classmethod
    def _build_invitation_text(
        cls,
        recipient_name: str | None,
        organization_name: str,
        team_name: str | None,
        role: str,
        invite_url: str,
    ) -> str:
        name_display = recipient_name if recipient_name else "there"
        team_text = f"Team: {team_name}\n" if team_name else ""
        return (
            f"Hi {name_display},\n\n"
            f"You have been invited to join {organization_name} on KAIRO.\n\n"
            f"Organization: {organization_name}\n"
            f"{team_text}"
            f"Role: {role}\n"
            f"Expiration: 7 Days\n\n"
            f"Accept your invitation and setup the KAIRO Desktop HUD here:\n"
            f"{invite_url}\n\n"
            f"--\n"
            f"KAIRO Work Continuity Engine\n"
        )

    @classmethod
    def _send_smtp_sync(
        cls,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str,
    ) -> bool:
        """Synchronous SMTP transaction executed in worker thread."""
        settings = get_settings()

        if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
            logger.warning(
                "SMTP credentials not configured (SMTP_USER/SMTP_PASSWORD empty). "
                f"Skipping email delivery to {to_email}."
            )
            return False

        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        message["To"] = to_email

        message.attach(MIMEText(text_body, "plain", "utf-8"))
        message.attach(MIMEText(html_body, "html", "utf-8"))

        try:
            context = ssl.create_default_context()
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
                server.starttls(context=context)
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(settings.SMTP_FROM_EMAIL, [to_email], message.as_string())

            logger.info(
                f"Email successfully delivered to {to_email} (Subject: '{subject}')"
            )
            return True
        except Exception as exc:
            logger.error(
                f"Failed to send email to {to_email} via {settings.SMTP_HOST}:{settings.SMTP_PORT}: {exc}"
            )
            return False

    @classmethod
    async def send_invitation_email(
        cls,
        to_email: str,
        recipient_name: str | None,
        organization_id: str,
        team_name: str | None,
        role: str,
        invite_token: str,
    ) -> bool:
        """
        Dispatches a responsive HTML invitation email asynchronously via thread pool.
        Fails safely without raising exceptions to API callers.
        """
        settings = get_settings()
        base_url = settings.WEB_APP_URL.rstrip('/')
        if settings.APP_ENV.lower() == "production" and ("localhost" in base_url or "127.0.0.1" in base_url):
            base_url = "https://kairo-web-91or.onrender.com"

        invite_url = f"{base_url}/auth?invite={invite_token}"
        org_display = organization_id.capitalize()

        subject = f"You've been invited to join {org_display} on KAIRO"
        html_body = cls._build_invitation_html(
            recipient_name=recipient_name,
            organization_name=org_display,
            team_name=team_name,
            role=role,
            invite_url=invite_url,
            base_url=base_url,
        )
        text_body = cls._build_invitation_text(
            recipient_name=recipient_name,
            organization_name=org_display,
            team_name=team_name,
            role=role,
            invite_url=invite_url,
        )

        return await asyncio.to_thread(
            cls._send_smtp_sync,
            to_email=to_email,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
        )
