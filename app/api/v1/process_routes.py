# File: app/api/v1/process_routes.py
# New JSON API endpoint for the Voice Frontend (React App)

import logging
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.services.process_query import process_query
from app.core.security import is_gate_open, verify_access_key

logger = logging.getLogger(__name__)

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class QueryRequest(BaseModel):
    input: str
    lat: Optional[float] = None
    lng: Optional[float] = None
    user_id: Optional[str] = "web_voice_user"


@router.post("/process-query")
async def handle_query(
    req: QueryRequest,
    db: Session = Depends(get_db),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    key: Optional[str] = Query(None)
):
    """
    JSON endpoint for the Voice Frontend.
    Accepts user speech as text, runs it through the central AI orchestrator,
    and returns a clean JSON response for the React app to speak aloud.
    """
    # ── Security: Check if system gate is open ──
    if not is_gate_open():
        logger.warning("Blocked process-query request - System Gate is Closed.")
        raise HTTPException(status_code=503, detail="Service temporarily paused by administrator.")

    # ── Security: Validate access key ──
    # Check either the Header X-API-Key or Query Parameter key
    client_key = x_api_key or key
    if not verify_access_key(client_key):
        logger.warning(f"Unauthorized process-query request for user '{req.user_id}' - Invalid key.")
        raise HTTPException(status_code=403, detail="Invalid or missing Access Key.")

    logger.info(f"Voice query received for user '{req.user_id}': {req.input[:60]}...")
    return await process_query(
        input_text=req.input,
        db=db,
        source="voice",
        lat=req.lat,
        lng=req.lng,
        user_id=req.user_id,
    )
