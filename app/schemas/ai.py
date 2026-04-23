from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional

class ChatIntent(str, Enum):
    SHOW_MENU = "show_menu"
    VACCINE_SCHEDULE = "vaccine_schedule"
    FIND_DOCTORS = "find_doctors"
    GET_ALERTS = "get_alerts"
    EMERGENCY = "emergency"
    GENERAL_CHAT = "general_chat"

class AIDataDetails(BaseModel):
    hospital_name: Optional[str] = Field(None, description="Extracted hospital name")
    date_of_birth: Optional[str] = Field(None, description="Extracted DOB (YYYY-MM-DD)")
    emergency_type: Optional[str] = Field(None, description="Type of emergency detected")
    confidence_score: float = Field(0.0, description="AI confidence in intent routing (0.0 to 1.0)")

class AIStructuredResponse(BaseModel):
    intent: ChatIntent
    data: AIDataDetails = Field(default_factory=AIDataDetails)
    reply: str
