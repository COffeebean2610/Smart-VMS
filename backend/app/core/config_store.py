import os
import json
import logging
from pathlib import Path
from typing import Optional
from app.core.paths import get_app_data_dir, is_packaged
from app.core.security import encrypt_secret, decrypt_secret

logger = logging.getLogger(__name__)


def get_config_file_path() -> Path:
    """
    Get the path to the secure local configuration file.
    In Packaged / Desktop mode: AppData/Local/SmartVMS/config.enc
    In Development mode: backend/config.enc (or backend/.env)
    """
    return get_app_data_dir() / "config.enc"


def load_secure_config() -> dict:
    """
    Load and decrypt local application configuration.
    """
    config_file = get_config_file_path()
    if not config_file.exists():
        return {}

    try:
        raw_content = config_file.read_text(encoding="utf-8").strip()
        if not raw_content:
            return {}

        decrypted_json = decrypt_secret(raw_content)
        if not decrypted_json:
            return {}

        return json.loads(decrypted_json)
    except Exception as e:
        logger.error(f"[CONFIG STORE] Error loading secure config: {e}")
        return {}


def save_secure_config(config_data: dict) -> bool:
    """
    Encrypts and saves application configuration securely to disk.
    """
    try:
        config_file = get_config_file_path()
        config_json = json.dumps(config_data, indent=2)
        encrypted_content = encrypt_secret(config_json)

        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text(encrypted_content, encoding="utf-8")
        logger.info(f"[CONFIG STORE] Saved encrypted configuration to: {config_file}")
        return True
    except Exception as e:
        logger.error(f"[CONFIG STORE] Error saving secure config: {e}")
        return False


def get_mongo_uri() -> Optional[str]:
    """
    Retrieves the active MongoDB URI.
    Priority:
    1. Secure encrypted config file (if configured via first-run UI)
    2. MONGO_URI environment variable (from .env or process env)
    """
    # 1. Check secure local config store
    config = load_secure_config()
    stored_uri = config.get("mongoUri", "").strip()
    if stored_uri and not is_placeholder_uri(stored_uri):
        return stored_uri

    # 2. Check environment variable
    env_uri = os.getenv("MONGO_URI", "").strip()
    if env_uri and not is_placeholder_uri(env_uri):
        return env_uri

    return None


def set_mongo_uri(uri: str) -> bool:
    """
    Updates and securely persists the active MongoDB URI.
    """
    clean_uri = uri.strip()
    config = load_secure_config()
    config["mongoUri"] = clean_uri
    return save_secure_config(config)


def is_placeholder_uri(uri: str) -> bool:
    """
    Checks if a URI string is an unconfigured template/placeholder.
    """
    if not uri:
        return True
    lowers = uri.lower()
    return "<username>" in lowers or "<password>" in lowers or "localhost:27017" in lowers and not os.getenv("MONGO_URI")


def get_telegram_config() -> dict:
    """
    Retrieves active Telegram alert configuration.
    Priority:
    1. Secure encrypted config file (config.enc)
    2. Environment variables (.env)
    """
    config = load_secure_config()

    # Enabled status
    if "telegramEnabled" in config:
        enabled = bool(config["telegramEnabled"])
    else:
        raw_enabled = os.getenv("TELEGRAM_ENABLED", "false").strip().lower()
        enabled = raw_enabled in ("true", "1", "yes", "on")

    # Bot token
    stored_token = config.get("telegramBotToken", "").strip()
    bot_token = stored_token if stored_token else os.getenv("TELEGRAM_BOT_TOKEN", "").strip()

    # Chat ID(s)
    stored_chat_id = config.get("telegramChatId", "").strip()
    chat_id = stored_chat_id if stored_chat_id else os.getenv("TELEGRAM_CHAT_ID", "").strip()

    return {
        "enabled": enabled,
        "botToken": bot_token,
        "chatId": chat_id,
    }


def set_telegram_config(enabled: bool, bot_token: Optional[str] = None, chat_id: Optional[str] = None) -> bool:
    """
    Updates and securely persists Telegram alert configuration.
    If bot_token is empty or None, retains the previously saved bot token if present.
    """
    config = load_secure_config()
    config["telegramEnabled"] = bool(enabled)

    if bot_token is not None:
        clean_token = bot_token.strip()
        # If user did not change/override the masked token or provided a real token
        if clean_token and not clean_token.startswith("••••"):
            config["telegramBotToken"] = clean_token

    if chat_id is not None:
        config["telegramChatId"] = chat_id.strip()

    return save_secure_config(config)


def is_first_run_completed() -> bool:
    """
    Checks if initial setup wizard has been completed.
    """
    config = load_secure_config()
    return bool(config.get("firstRunCompleted", False))


def set_first_run_completed(completed: bool = True) -> bool:
    """
    Updates and securely persists the first-run completion flag.
    """
    config = load_secure_config()
    config["firstRunCompleted"] = bool(completed)
    return save_secure_config(config)


