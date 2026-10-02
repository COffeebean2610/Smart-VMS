import logging
from typing import Any, Dict
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from app.db.database import get_db_status_info, connect_to_mongo, db_manager
from app.core.config_store import get_mongo_uri, set_mongo_uri, is_placeholder_uri, is_first_run_completed, set_first_run_completed
from app.services.telegram_service import TelegramService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/system", tags=["System"])


class DBConfigPayload(BaseModel):
    mongoUri: str = Field(..., description="MongoDB Atlas Connection String")


@router.get("/first-run", response_model=Dict[str, Any])
async def get_first_run_status():
    """
    Returns initial onboarding setup status.
    """
    uri = get_mongo_uri()
    mongo_configured = bool(uri and not is_placeholder_uri(uri))
    telegram_service = TelegramService()
    
    return {
        "firstRunCompleted": is_first_run_completed(),
        "mongoConfigured": mongo_configured,
        "telegramConfigured": telegram_service.is_configured(),
    }


@router.post("/first-run/complete", response_model=Dict[str, Any])
async def complete_first_run():
    """
    Marks initial onboarding setup wizard as completed in secure DPAPI config store.
    """
    save_success = set_first_run_completed(True)
    return {
        "success": save_success,
        "message": "First-run setup completed successfully.",
    }


@router.get("/db-status", response_model=Dict[str, Any])
async def get_db_status():
    """
    Returns live database connection status.
    Safe endpoint: Never exposes secrets or connection string.
    """
    return get_db_status_info()


@router.get("/db-config", response_model=Dict[str, Any])
async def get_db_config():
    """
    Returns database configuration metadata (without exposing credentials).
    """
    uri = get_mongo_uri()
    configured = bool(uri and not is_placeholder_uri(uri))
    return {
        "configured": configured,
        "status": db_manager.status.value,
        "message": "MongoDB Atlas URI is configured." if configured else "MongoDB Atlas URI is missing or placeholder.",
    }


@router.post("/db-config", response_model=Dict[str, Any])
async def update_db_config(payload: DBConfigPayload):
    """
    Validates, tests, and securely saves a new MongoDB connection string.
    If valid: Persists encrypted configuration locally and connects.
    If invalid: Returns clean 400 error without exposing raw exception secrets.
    """
    clean_uri = payload.mongoUri.strip()
    if not clean_uri or is_placeholder_uri(clean_uri):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid MongoDB URI format. Please provide a valid Atlas connection string.",
        )

    logger.info("[SYSTEM API] Testing new MongoDB Atlas connection string...")
    success = await connect_to_mongo(uri_override=clean_uri)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to connect to MongoDB Atlas. Please check your connection string and Internet connection.",
        )

    # Persist encrypted URI locally
    save_success = set_mongo_uri(clean_uri)
    if not save_success:
        logger.warning("[SYSTEM API] Connection succeeded but failed to save encrypted configuration to disk.")

    return {
        "success": True,
        "status": db_manager.status.value,
        "message": "MongoDB Atlas connection configured and saved successfully!",
    }

