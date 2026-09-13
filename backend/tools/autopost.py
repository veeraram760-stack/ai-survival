"""
Auto-posting tools for agents - Telegram, Discord, Email
"""
from typing import Dict, Any, Optional
from .base import Tool, tool_registry
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import httpx

logger = logging.getLogger("ai_survival.tools.autopost")


class TelegramPostTool(Tool):
    """Post content to Telegram channel or chat"""

    def __init__(self):
        super().__init__(
            name="telegram_post",
            description="Post content to Telegram channel/group using bot token",
            cost=0.0,
        )
        self.bot_token = None

    async def execute(
        self,
        content: str,
        chat_id: str = "",
        parse_mode: str = "HTML",
        **kwargs
    ) -> Dict[str, Any]:
        from config.settings import settings
        self.bot_token = kwargs.get("bot_token") or getattr(settings, "telegram_bot_token", None) or ""
        chat_id = kwargs.get("chat_id") or chat_id or getattr(settings, "telegram_chat_id", "")
        
        if not self.bot_token or not chat_id:
            return {
                "status": "failed",
                "error": "Telegram bot token and chat_id required. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env",
                "real": True,
            }

        try:
            import httpx
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            text = content or ""
            if len(text) > 4096:
                text = text[:4090] + "\n...[truncated]"
            payload = {
                "chat_id": str(chat_id),
                "text": text,
                "parse_mode": parse_mode,
            }
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                return {
                    "status": "success",
                    "platform": "telegram",
                    "message_id": data.get("result", {}).get("message_id"),
                    "chat_id": chat_id,
                    "content": text,
                    "real": True,
                }
        except httpx.HTTPStatusError as e:
            error_text = str(e)
            response_body = ""
            if e.response is not None:
                try:
                    response_body = e.response.text
                except Exception:
                    response_body = "unreadable"
            logger.error(f"Telegram post failed: chat_id={chat_id}, status={e.response.status_code if e.response else '?'}, body={response_body}")
            if e.response is not None and e.response.status_code == 400:
                try:
                    text = content or ""
                    if len(text) > 4096:
                        text = text[:4090] + "\n...[truncated]"
                    payload = {
                        "chat_id": str(chat_id),
                        "text": text,
                    }
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        response = await client.post(url, json=payload)
                        response.raise_for_status()
                        data = response.json()
                        return {
                            "status": "success",
                            "platform": "telegram",
                            "message_id": data.get("result", {}).get("message_id"),
                            "chat_id": chat_id,
                            "content": text,
                            "real": True,
                            "note": "Sent without parse_mode due to HTML formatting issue",
                        }
                except Exception as fallback_error:
                    logger.error(f"Telegram fallback failed: chat_id={chat_id}, error={fallback_error}")
                    return {"status": "failed", "platform": "telegram", "error": str(fallback_error), "real": True}
            return {"status": "failed", "platform": "telegram", "error": error_text, "real": True}
        except Exception as e:
            error_text = str(e)
            logger.error(f"Telegram post failed: chat_id={chat_id}, error={error_text}")
            return {"status": "failed", "platform": "telegram", "error": error_text, "real": True}


class DiscordPostTool(Tool):
    """Post content to Discord channel via webhook"""

    def __init__(self):
        super().__init__(
            name="discord_post",
            description="Post content to Discord channel via webhook",
            cost=0.0,
        )

    async def execute(
        self,
        content: str,
        webhook_url: str = "",
        username: str = "AI Agent",
        **kwargs
    ) -> Dict[str, Any]:
        from config.settings import settings
        webhook_url = kwargs.get("webhook_url") or webhook_url or getattr(settings, "discord_webhook_url", "")
        
        if not webhook_url:
            return {
                "status": "failed",
                "error": "Discord webhook URL required. Set DISCORD_WEBHOOK_URL in .env",
                "real": True,
            }

        try:
            import httpx
            if len(content) > 2000:
                content = content[:1997] + "..."
            payload = {
                "content": content,
                "username": username,
            }
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(webhook_url, json=payload)
                response.raise_for_status()
                return {
                    "status": "success",
                    "platform": "discord",
                    "webhook_url": webhook_url,
                    "content": content,
                    "real": True,
                }
        except Exception as e:
            return {"status": "failed", "platform": "discord", "error": str(e), "real": True}


class EmailSendTool(Tool):
    """Send email via SMTP"""

    def __init__(self):
        super().__init__(
            name="email_send",
            description="Send email via SMTP",
            cost=0.0,
        )

    async def execute(
        self,
        subject: str,
        body: str,
        to_email: str = "",
        from_email: str = "",
        smtp_host: str = "",
        smtp_port: int = 587,
        smtp_user: str = "",
        smtp_password: str = "",
        **kwargs
    ) -> Dict[str, Any]:
        from config.settings import settings
        to_email = kwargs.get("to_email") or to_email or getattr(settings, "default_notification_email", "")
        from_email = kwargs.get("from_email") or from_email or getattr(settings, "smtp_host", "")
        smtp_host = kwargs.get("smtp_host") or smtp_host or getattr(settings, "smtp_host", "")
        smtp_port = kwargs.get("smtp_port") or smtp_port or getattr(settings, "smtp_port", 587)
        smtp_user = kwargs.get("smtp_user") or smtp_user or getattr(settings, "smtp_user", "")
        smtp_password = kwargs.get("smtp_password") or smtp_password or getattr(settings, "smtp_password", "")
        
        if not all([to_email, smtp_host, smtp_user, smtp_password]):
            return {
                "status": "failed",
                "error": "SMTP configuration incomplete. Set SMTP_HOST, SMTP_USER, SMTP_PASSWORD in .env",
                "real": True,
            }

        try:
            msg = MIMEMultipart()
            msg["From"] = from_email or smtp_user
            msg["To"] = to_email
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.send_message(msg)

            return {
                "status": "success",
                "platform": "email",
                "to_email": to_email,
                "subject": subject,
                "real": True,
            }
        except Exception as e:
            return {"status": "failed", "platform": "email", "error": str(e), "real": True}


# Register tools
tool_registry.register(TelegramPostTool())
tool_registry.register(DiscordPostTool())
tool_registry.register(EmailSendTool())
