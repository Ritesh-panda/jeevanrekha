# File: app/services/ai_service.py

import json
import logging
import redis
import google.generativeai as genai
from app.core.config import settings
from app.schemas.ai import AIStructuredResponse, ChatIntent, AIDataDetails

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# --- Redis Setup ---
redis_client = None
try:
    redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    redis_client.ping()
    logger.info("--- Successfully connected to Redis. ---")
except Exception as e:
    logger.error(f"--- ERROR: Could not connect to Redis: {e} ---")

# --- Gemini Model Setup ---
model = None
try:
    if settings.GEMINI_API_KEY and settings.GEMINI_API_KEY != "YOUR_GEMINI_API_KEY_HERE":
        genai.configure(api_key=settings.GEMINI_API_KEY)
        # Upgraded to gemini-2.0-flash per audit recommendations
        model = genai.GenerativeModel('gemini-2.0-flash-lite-001')
        logger.info("--- Successfully connected to Gemini API. ---")
    else:
        logger.warning("--- WARNING: GEMINI_API_KEY is not set. AI service will be disabled. ---")
except Exception as e:
    logger.error(f"--- ERROR: Failed to configure Gemini API: {e} ---")

SYSTEM_PROMPT = """You are Arogya Mitra, a highly precise AI Healthcare Routing Engine & Emergency Assistant for India.
Your SOLE purpose is to classify user queries and output a strictly formatted JSON object.
DO NOT output conversational text outside of the JSON block.
DO NOT wrap the response in markdown blocks like ```json.

ALLOWED INTENTS:
- "emergency": Life-threatening situations (heart attack, severe bleeding, breathing issues, severe trauma).
- "find_doctors": User wants to find doctors at a specific hospital.
- "vaccine_schedule": User is asking for child vaccination dates based on a DOB.
- "get_alerts": User asks for general health news or alerts.
- "show_menu": User is greeting or asking what you can do.
- "general_chat": Non-emergency medical advice, symptom analysis, or anything else.

RULES:
1. Always output valid JSON exactly matching this structure:
{
  "intent": "<ONE_OF_ALLOWED_INTENTS>",
  "data": {
     "emergency_type": "<Description if emergency, else null>",
     "hospital_name": "<Extracted hospital name, else null>",
     "date_of_birth": "<YYYY-MM-DD if vaccine_schedule, else null>",
     "confidence_score": <Float 0.0 to 1.0 representing your confidence in this classification>
  },
  "reply": "<Your empathetic, calm response if general_chat or emergency. Empty otherwise.>"
}
"""

def get_ai_response(user_id: str, user_message: str) -> AIStructuredResponse:
    if not model or not redis_client:
        return AIStructuredResponse(
            intent=ChatIntent.GENERAL_CHAT,
            reply="I'm sorry, a core service is not configured correctly. Please check the logs."
        )

    history_key = f"history:{user_id}"
    try:
        conversation_history = json.loads(redis_client.get(history_key) or "[]")
    except Exception as e:
        logger.warning(f"--- Redis/JSON Error: {e}. Resetting history. ---")
        conversation_history = []

    # Add the new user message
    conversation_history.append({"role": "user", "parts": [user_message]})

    # Force JSON format and low temperature for determinism
    generation_config = genai.types.GenerationConfig(
        response_mime_type="application/json",
        temperature=0.1
    )

    try:
        chat = model.start_chat(history=conversation_history[:-1])
        response = chat.send_message(
            f"{SYSTEM_PROMPT}\n\nUser: {user_message}",
            generation_config=generation_config
        )
        
        # Strip markdown safely
        raw_text = response.text.strip().removeprefix('```json').removeprefix('```').removesuffix('```').strip()
        raw_data = json.loads(raw_text)
        
        structured_response = AIStructuredResponse(**raw_data)
        logger.info(f"Route: {structured_response.intent.value} | Confidence: {structured_response.data.confidence_score}")

        # Add AI reply to history
        conversation_history.append({"role": "model", "parts": [str(raw_data)]})
        short_history = conversation_history[-6:]
        redis_client.set(history_key, json.dumps(short_history))
        redis_client.expire(history_key, 3600)

        return structured_response

    except json.JSONDecodeError as parse_err:
        logger.error(f"JSON Parse Error. Fallback triggered. Raw Output: {response.text}")
    except ValueError as val_err:
         logger.error(f"Pydantic Validation Error: {val_err}. Fallback triggered.")
    except Exception as e:
        logger.error(f"Gemini API Error: {e}")

    # Fallback response
    return AIStructuredResponse(
        intent=ChatIntent.GENERAL_CHAT,
        reply="I'm sorry, I'm having difficulty processing that right now. Could you rephrase your question?"
    )