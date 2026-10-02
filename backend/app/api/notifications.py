import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.services.telegram_service import TelegramService
from app.core.config_store import set_telegram_config, get_telegram_config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


class TelegramTestResponse(BaseModel):
    success: bool
    message: str


class TelegramStatusResponse(BaseModel):
    enabled: bool
    configured: bool
    hasBotToken: bool
    maskedToken: str
    chatId: str


class TelegramConfigPayload(BaseModel):
    enabled: bool = True
    botToken: Optional[str] = Field(None, description="Telegram Bot Token")
    chatId: Optional[str] = Field(None, description="Telegram Chat ID(s)")


@router.get("/telegram/status", response_model=TelegramStatusResponse)
async def get_telegram_status():
    telegram_service = TelegramService()
    config = get_telegram_config()
    raw_token = config["botToken"]
    has_token = bool(raw_token)
    
    masked_token = ""
    if has_token:
        masked_token = f"••••••••{raw_token[-4:]}" if len(raw_token) > 4 else "••••••••"

    return TelegramStatusResponse(
        enabled=telegram_service.enabled,
        configured=telegram_service.is_configured(),
        hasBotToken=has_token,
        maskedToken=masked_token,
        chatId=config["chatId"],
    )


@router.post("/telegram/config")
async def update_telegram_config(payload: TelegramConfigPayload):
    """
    Saves Telegram configuration securely to DPAPI config_store.
    Does not expose sensitive raw bot token in response.
    """
    save_success = set_telegram_config(
        enabled=payload.enabled,
        bot_token=payload.botToken,
        chat_id=payload.chatId,
    )

    if not save_success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save Telegram configuration to secure store.",
        )

    # Reload TelegramService singleton configuration immediately
    TelegramService().reload_config()

    return {
        "success": True,
        "message": "Telegram configuration saved successfully!",
        "configured": TelegramService().is_configured(),
    }


@router.post("/telegram/test", response_model=TelegramTestResponse)
async def test_telegram_alert():
    telegram_service = TelegramService()
    if not telegram_service.is_configured():
        return TelegramTestResponse(
            success=False,
            message="Telegram is disabled or not configured. Please save Bot Token and Chat ID.",
        )

    test_message = "Smart VMS Telegram test alert — connection successful."
    success = await telegram_service.send_telegram_message(test_message)

    if success:
        return TelegramTestResponse(
            success=True,
            message="Smart VMS Telegram test alert — connection successful.",
        )
    else:
        return TelegramTestResponse(
            success=False,
            message="Failed to send Telegram test message. Please verify your Bot Token and Chat ID.",
        )

