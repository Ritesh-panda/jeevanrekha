# File: app/api/v1/admin_routes.py

import logging
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Optional
from app.core.config import settings
from app.core.security import is_gate_open, set_gate_state, verify_access_key

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin")

class ToggleGateRequest(BaseModel):
    admin_password: str
    gate_open: bool

@router.get("/status")
def get_system_status(key: Optional[str] = None):
    """
    Check current authorization status of the API.
    Returns whether the gate is open and if a provided key is valid.
    """
    gate_active = is_gate_open()
    key_configured = settings.SYSTEM_ACCESS_KEY is not None and settings.SYSTEM_ACCESS_KEY != ""
    is_valid = verify_access_key(key) if key_configured else True
    
    return {
        "gate_open": gate_active,
        "key_required": key_configured,
        "key_valid": is_valid,
        "status": "ready" if (gate_active and is_valid) else ("paused" if not gate_active else "unauthorized")
    }

@router.post("/toggle")
def toggle_system_gate(req: ToggleGateRequest):
    """
    Toggle the system gate status (open/close).
    Requires a valid admin password.
    """
    # Safeguard against unconfigured admin password
    admin_pass = settings.ADMIN_PASSWORD or "admin123"
    
    if req.admin_password != admin_pass:
        logger.warning("Unauthorized attempt to toggle system gate!")
        raise HTTPException(status_code=401, detail="Incorrect admin password")
        
    set_gate_state(req.gate_open)
    return {
        "message": f"System gate successfully {'opened' if req.gate_open else 'closed'}",
        "gate_open": is_gate_open()
    }
