# File: app/core/security.py

import logging
import redis
from app.core.config import settings

logger = logging.getLogger(__name__)

# Fallback in-memory gate state
_in_memory_gate = settings.SYSTEM_GATE_OPEN

# Initialize Redis client if configured
redis_client = None
if settings.REDIS_URL:
    try:
        redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        logger.info("--- ✅ Security system: Redis storage ready. ---")
    except Exception as e:
        logger.warning(f"--- ⚠️ Security system: Redis connection failed: {e}. Falling back to in-memory gate storage. ---")

def is_gate_open() -> bool:
    """Check if the system gate is open to process AI requests."""
    global _in_memory_gate
    if redis_client:
        try:
            val = redis_client.get("system_gate_open")
            if val is not None:
                return val.lower() == "true"
        except Exception as e:
            logger.error(f"Error reading gate status from Redis: {e}")
    
    return _in_memory_gate

def set_gate_state(open_state: bool):
    """Set the system gate state (True for open, False for closed)."""
    global _in_memory_gate
    if redis_client:
        try:
            redis_client.set("system_gate_open", "true" if open_state else "false")
            logger.info(f"--- 🔒 Gate status updated in Redis: {open_state} ---")
            return
        except Exception as e:
            logger.error(f"Error writing gate status to Redis: {e}")
    
    _in_memory_gate = open_state
    logger.info(f"--- 🔒 Gate status updated in memory: {open_state} ---")

def verify_access_key(client_key: str | None) -> bool:
    """
    Verify if the client-provided key matches the configured SYSTEM_ACCESS_KEY.
    If no key is configured, validation is bypassed (returns True).
    """
    if not settings.SYSTEM_ACCESS_KEY:
        return True
    return client_key == settings.SYSTEM_ACCESS_KEY
