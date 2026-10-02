import asyncio
import logging
import re
import os
import time
from enum import Enum
from typing import Any, Optional, Dict
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.paths import load_environment
from app.core.config_store import get_mongo_uri, set_mongo_uri

logger = logging.getLogger(__name__)

# Timeout configurations for desktop resilience (in milliseconds)
SERVER_SELECTION_TIMEOUT_MS = 5000  # 5s server selection timeout
CONNECT_TIMEOUT_MS = 5000           # 5s initial connection timeout
SOCKET_TIMEOUT_MS = 10000           # 10s socket timeout


class DBStatus(str, Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    RECONNECTING = "reconnecting"
    UNCONFIGURED = "unconfigured"


class DatabaseManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None
        self.status: DBStatus = DBStatus.UNCONFIGURED
        self.last_error: Optional[str] = None
        self.last_checked: float = 0.0
        self.reconnect_task: Optional[asyncio.Task] = None
        self.is_reconnecting: bool = False

    def sanitize_uri_for_logging(self, uri: str) -> str:
        """
        Redacts username and password credentials from connection strings for safe logging.
        """
        if not uri:
            return "<empty>"
        # Redact mongodb (+srv) credentials: mongodb+srv://user:pass@host/db
        return re.sub(r"://([^:]+):([^@]+)@", "://***:***@", uri)


db_manager = DatabaseManager()


async def connect_to_mongo(uri_override: Optional[str] = None) -> bool:
    """
    Connects to MongoDB Atlas using defined connection timeouts.
    Never throws unhandled exceptions that block backend application startup.
    """
    load_environment()
    uri = uri_override or get_mongo_uri()

    if not uri:
        logger.warning("[DATABASE] No valid MongoDB URI configured. Operating in UNCONFIGURED state.")
        db_manager.status = DBStatus.UNCONFIGURED
        db_manager.last_error = "MongoDB URI not configured."
        return False

    db_manager.status = DBStatus.CONNECTING
    sanitized_uri = db_manager.sanitize_uri_for_logging(uri)
    logger.info(f"[DATABASE] Attempting connection to MongoDB ({sanitized_uri})...")

    try:
        try:
            current_loop = asyncio.get_running_loop()
            logger.info(f"[MONGO] Client initialization loop id: {id(current_loop)}")
        except RuntimeError:
            logger.warning("[MONGO] Initializing client outside running event loop")

        # Create AsyncIOMotorClient with configurable timeouts
        client = AsyncIOMotorClient(
            uri,
            serverSelectionTimeoutMS=SERVER_SELECTION_TIMEOUT_MS,
            connectTimeoutMS=CONNECT_TIMEOUT_MS,
            socketTimeoutMS=SOCKET_TIMEOUT_MS,
        )

        # Fast non-blocking ping verification with 5-second timeout
        await client.admin.command("ping")

        db_manager.client = client
        db_manager.db = client.get_database("smart_vms")
        db_manager.status = DBStatus.CONNECTED
        db_manager.last_error = None
        db_manager.last_checked = time.time()

        logger.info("[DATABASE] Successfully connected to MongoDB database 'smart_vms'!")
        return True

    except Exception as e:
        error_msg = f"MongoDB Connection Error: {str(e)}"
        logger.error(f"[DATABASE ERROR] {error_msg}")
        db_manager.status = DBStatus.DISCONNECTED
        db_manager.last_error = str(e)
        db_manager.last_checked = time.time()
        
        # Start background automatic reconnection loop if disconnected
        start_auto_reconnect()
        return False


async def close_mongo_connection():
    """
    Closes active MongoDB connection and cancels reconnection tasks.
    """
    if db_manager.reconnect_task and not db_manager.reconnect_task.done():
        db_manager.reconnect_task.cancel()

    if db_manager.client:
        logger.info("[DATABASE] Closing MongoDB connection...")
        db_manager.client.close()
        db_manager.client = None
        db_manager.db = None
        db_manager.status = DBStatus.DISCONNECTED
        logger.info("[DATABASE] MongoDB connection closed.")


def get_database() -> Optional[Any]:
    """
    Returns active Motor database handle.
    Returns None if disconnected or unconfigured without raising exceptions.
    """
    if db_manager.status == DBStatus.CONNECTED and db_manager.db is not None:
        return db_manager.db

    # Lazy auto-reconnect trigger if database accessed while disconnected
    if db_manager.status in (DBStatus.DISCONNECTED, DBStatus.UNCONFIGURED):
        start_auto_reconnect()

    return db_manager.db


def start_auto_reconnect():
    """
    Schedules background auto-reconnection task if not already running.
    """
    if db_manager.is_reconnecting:
        return

    try:
        loop = asyncio.get_running_loop()
        if db_manager.reconnect_task is None or db_manager.reconnect_task.done():
            db_manager.reconnect_task = loop.create_task(_auto_reconnect_loop())
    except RuntimeError:
        # Loop not running yet (will be started during lifespan)
        pass


async def _auto_reconnect_loop():
    """
    Background periodic reconnection task with exponential/fixed backoff.
    Runs without consuming excessive CPU or network bandwidth.
    """
    db_manager.is_reconnecting = True
    backoff = 5.0
    max_backoff = 30.0

    try:
        while True:
            await asyncio.sleep(backoff)

            if db_manager.status == DBStatus.CONNECTED:
                # Test active connection health periodically
                try:
                    if db_manager.client:
                        await db_manager.client.admin.command("ping")
                        db_manager.last_checked = time.time()
                        backoff = 10.0  # Normal health check interval
                        continue
                except Exception as e:
                    logger.warning(f"[DATABASE] Connection health check failed: {e}")
                    db_manager.status = DBStatus.DISCONNECTED
                    db_manager.last_error = str(e)

            # Reconnection attempt
            uri = get_mongo_uri()
            if not uri:
                db_manager.status = DBStatus.UNCONFIGURED
                backoff = 10.0
                continue

            db_manager.status = DBStatus.RECONNECTING
            logger.info(f"[DATABASE RECONNECT] Retrying MongoDB connection in background...")

            success = await connect_to_mongo(uri)
            if success:
                logger.info("[DATABASE RECONNECT] Background reconnection successful!")
                backoff = 10.0
            else:
                backoff = min(max_backoff, backoff * 1.5)

    except asyncio.CancelledError:
        logger.debug("[DATABASE RECONNECT] Reconnection loop cancelled.")
    finally:
        db_manager.is_reconnecting = False


def get_db_status_info() -> Dict[str, Any]:
    """
    Returns clean, non-sensitive database status dictionary for the system API.
    """
    configured = bool(get_mongo_uri())
    
    if db_manager.status == DBStatus.CONNECTED:
        msg = "Connected to MongoDB Atlas"
    elif db_manager.status == DBStatus.RECONNECTING:
        msg = "Attempting reconnection to MongoDB Atlas..."
    elif db_manager.status == DBStatus.UNCONFIGURED:
        msg = "MongoDB Atlas URI not configured"
    else:
        msg = "MongoDB Atlas unavailable (Check internet connection)"

    return {
        "status": db_manager.status.value,
        "configured": configured,
        "message": msg,
        "database": "smart_vms" if db_manager.status == DBStatus.CONNECTED else None,
        "lastError": db_manager.last_error if db_manager.status != DBStatus.CONNECTED else None,
        "serverSelectionTimeoutMS": SERVER_SELECTION_TIMEOUT_MS,
    }
