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

        team_stub_row = (
            f"""
            <tr>
              <td style="border-top: 1px dotted #57534E; padding-top: 18px;">
                <p style="margin: 0 0 3px; font-size: 10px; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; color: #A8A29E;">Team</p>
                <p style="margin: 0 0 18px; font-size: 14px; font-weight: 700; color: #FFFDF9;">{team_name}</p>
              </td>
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
  <meta name="color-scheme" content="light">
  <meta name="supported-color-schemes" content="light">
  <title>Invitation to join {organization_name} on KAIRO</title>
  <!--[if mso]>
  <noscript>
    <xml>
      <o:OfficeDocumentSettings>
        <o:PixelsPerInch>96</o:PixelsPerInch>
      </o:OfficeDocumentSettings>
    </xml>
  </noscript>
  <![endif]-->
  <style>
    body, table, td, a {{ -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%; }}
    table, td {{ mso-table-lspace: 0pt; mso-table-rspace: 0pt; }}
    img {{ -ms-interpolation-mode: bicubic; border: 0; outline: none; text-decoration: none; }}
    body {{ margin: 0; padding: 0; width: 100% !important; height: 100% !important; }}

    @media only screen and (max-width: 620px) {{
      .email-wrapper {{ padding: 32px 14px !important; }}
      .mobile-full {{ width: 100% !important; max-width: 100% !important; }}
      .ticket {{ width: 100% !important; }}
      .stub-col {{ display: block !important; width: 100% !important; border-right: none !important; border-bottom: 2px dashed #F5F3EF !important; }}
      .main-col {{ display: block !important; width: 100% !important; }}
      .stub-pad {{ padding: 24px 22px 20px !important; }}
      .main-pad {{ padding: 28px 22px !important; }}
      .headline {{ font-size: 25px !important; }}
      .cta-table {{ width: 100% !important; }}
      .cta-link {{ display: block !important; width: 100% !important; box-sizing: border-box !important; text-align: center !important; }}
    }}

    @media only screen and (max-width: 380px) {{
      .email-wrapper {{ padding: 24px 10px !important; }}
      .stub-pad {{ padding: 20px 18px 16px !important; }}
      .main-pad {{ padding: 22px 18px !important; }}
      .headline {{ font-size: 22px !important; }}
      .stub-role {{ font-size: 18px !important; }}
      .lede {{ font-size: 13.5px !important; }}
    }}
  </style>
</head>
<body style="margin: 0; padding: 0; background-color: #F5F3EF; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1C1917;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #F5F3EF;">
    <tr>
      <td class="email-wrapper" align="center" style="padding: 56px 16px;">

        <!-- Wordmark -->
        <table role="presentation" class="mobile-full" width="640" cellspacing="0" cellpadding="0" style="width: 640px; max-width: 640px;">
          <tr>
            <td align="center" style="padding-bottom: 28px;">
              <a href="{base_url}" target="_blank" style="text-decoration: none;">
                <table role="presentation" cellspacing="0" cellpadding="0" style="display: inline-table;">
                  <tr>
                    <td valign="middle" style="padding-right: 9px;">
                      <img src="{logo_url}" alt="KAIRO" width="22" height="22" style="display: block; width: 22px; height: 22px; max-width: 22px; object-fit: contain; border-radius: 5px;" />
                    </td>
                    <td valign="middle">
                      <span style="font-size: 13px; font-weight: 800; letter-spacing: 0.22em; text-transform: uppercase; color: #1C1917;">KAIRO</span>
                    </td>
                  </tr>
                </table>
              </a>
            </td>
          </tr>
        </table>

        <!-- Ticket -->
        <table role="presentation" class="ticket" width="640" cellspacing="0" cellpadding="0" style="width: 640px; max-width: 640px; background-color: #FFFDF9;">
          <tr>

            <!-- Stub (left) -->
            <td class="stub-col" width="200" valign="top" style="width: 200px; background-color: #1C1917; border-right: 2px dashed #F5F3EF;">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" class="stub-pad" style="padding: 34px 26px;">
                <tr>
                  <td>
                    <p style="margin: 0 0 4px; font-size: 10px; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; color: #FF6A3D;">Admit one</p>
                    <p class="stub-role" style="margin: 0 0 4px; font-size: 20px; font-weight: 800; color: #FFFDF9; letter-spacing: -0.01em; word-break: break-word;">{role}</p>
                  </td>
                </tr>
                <tr>
                  <td style="border-top: 1px dotted #57534E; padding-top: 18px;">
                    <p style="margin: 0 0 3px; font-size: 10px; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; color: #A8A29E;">Organization</p>
                    <p style="margin: 0 0 18px; font-size: 14px; font-weight: 700; color: #FFFDF9; word-break: break-word;">{organization_name}</p>
                  </td>
                </tr>
                {team_stub_row}
                <tr>
                  <td style="border-top: 1px dotted #57534E; padding-top: 18px;">
                    <p style="margin: 0 0 3px; font-size: 10px; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; color: #A8A29E;">Valid for</p>
                    <p style="margin: 0; font-size: 14px; font-weight: 700; color: #FFFDF9;">7 days</p>
                  </td>
                </tr>
              </table>
            </td>

            <!-- Main (right) -->
            <td class="main-col" valign="top" style="background-color: #FFFDF9;">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" class="main-pad" style="padding: 40px 44px;">
                <tr>
                  <td>
                    <p style="margin: 0 0 10px; font-size: 12px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; color: #FF6A3D;">
                      You're invited
                    </p>
                    <h1 class="headline" style="margin: 0 0 18px; font-size: 30px; line-height: 1.15; font-weight: 800; color: #1C1917; letter-spacing: -0.02em; word-break: break-word;">
                      Join {organization_name}<br>on KAIRO
                    </h1>
                    <p class="lede" style="margin: 0 0 26px; font-size: 14.5px; line-height: 1.65; color: #57534E;">
                      Hi {name_display} — you've been asked to join the team. KAIRO keeps commits, tasks, and architecture decisions in sync automatically, so status meetings stop being necessary.
                    </p>

                    <!-- CTA -->
                    <table role="presentation" class="cta-table" cellspacing="0" cellpadding="0" style="margin-bottom: 24px;">
                      <tr>
                        <td style="background-color: #1C1917;">
                          <a href="{invite_url}" target="_blank" class="cta-link" style="display: inline-block; color: #FFFDF9; text-decoration: none; font-size: 14.5px; font-weight: 700; padding: 15px 30px; letter-spacing: -0.005em;">
                            Accept invitation &nbsp;&rarr;
                          </a>
                        </td>
                      </tr>
                    </table>

                    <p style="margin: 0 0 22px; font-size: 12.5px; line-height: 1.6; color: #A8A29E;">
                      Accepting sets up the KAIRO Desktop HUD (Windows, macOS, Linux) so your local git branches stay linked to your pod.
                    </p>

                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border-top: 1px dotted #E7E4DE;">
                      <tr>
                        <td style="padding-top: 18px;">
                          <p style="margin: 0; font-size: 11.5px; line-height: 1.6; color: #A8A29E; word-break: break-all;">
                            Link not working? Paste this into your browser —<br>
                            <a href="{invite_url}" style="color: #FF6A3D; text-decoration: none;">{invite_url}</a>
                          </p>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
            </td>

          </tr>
        </table>

        <!-- Footer -->
        <table role="presentation" class="mobile-full" width="640" cellspacing="0" cellpadding="0" style="width: 640px; max-width: 640px;">
          <tr>
            <td align="center" style="padding: 26px 16px 0;">
              <p style="margin: 0 0 4px; font-size: 12px; color: #A8A29E;">
                Sent by <a href="{base_url}" target="_blank" style="color: #1C1917; text-decoration: none; font-weight: 700;">KAIRO</a> &middot; Autonomous Work Continuity Engine
              </p>
              <p style="margin: 0; font-size: 11.5px; color: #C4C0B9;">
                Didn't expect this invitation? You can safely ignore this email.
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
