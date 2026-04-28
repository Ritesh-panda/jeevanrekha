# File: app/services/ai_service.py

import json
import logging
import re
from google import genai
from google.genai import types as genai_types
from groq import Groq
from app.core.config import settings
from app.schemas.ai import AIStructuredResponse, ChatIntent, AIDataDetails

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# --- GLOBAL IN-MEMORY CACHE ---
memory_cache = {}

# --- PRIMARY: Gemini 2.5 Flash ---
gemini_client = None
GEMINI_MODEL = "gemini-2.5-flash"
try:
    if settings.GEMINI_API_KEY and settings.GEMINI_API_KEY != "YOUR_GEMINI_API_KEY_HERE":
        gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
        logger.info(f"--- ✅ PRIMARY: {GEMINI_MODEL} ready (google.genai SDK). ---")
except Exception as e:
    logger.warning(f"--- ⚠️ Gemini setup failed: {e} ---")

# --- FALLBACK: Groq Llama-3 ---
groq_client = None
try:
    if settings.GROQ_API_KEY:
        groq_client = Groq(api_key=settings.GROQ_API_KEY)
        logger.info("--- ✅ FALLBACK: Groq Llama-3 ready. ---")
except Exception as e:
    logger.error(f"--- ERROR: Failed to configure Groq: {e} ---")

# --- SYSTEM PROMPT ---
SYSTEM_PROMPT = """You are JeevanRekha AI, a compassionate and world-class medical advisor.
You talk like a real human doctor who deeply cares about their patients.

CORE GUIDELINES:
- **EMPATHY FIRST**: If a user is suffering, acknowledge it immediately. Use words like "I'm so sorry you're going through this" or "That sounds very uncomfortable."
- **CONVERSATIONAL FLOW**: Don't just fire off a list of questions. Engage like standard Gemini would—natural, flowing, and intelligent.
- **PRECISION**: Give high-quality medical insights with a 🩺 emoji.
- **NO ROBOTIC TEMPLATES**: Avoid saying "Got your location" or "Analyzing symptoms" unless it fits naturally into a sentence.
- **SAFETY**: Never diagnose. If something is dangerous, firmly but kindly tell them to see a doctor or call 108.

OUTPUT FORMAT (Strict JSON only, no extra text):
{
  "intent": "emergency | find_doctors | vaccine_schedule | get_alerts | show_menu | general_chat",
  "data": {
     "emergency_type": "string or null",
     "hospital_name": "string or null",
     "date_of_birth": "YYYY-MM-DD or null",
     "confidence_score": 0.95
  },
  "reply": "Your warm, professional, and detailed response here. Use \\n\\n for clear spacing."
}
"""

def get_main_menu() -> str:
    """Returns a beautifully formatted WhatsApp main menu."""
    return (
        "👋 *Namaste! I am Arogya Mitra, your Digital Health Sahayaka.*\n\n"
        "How can I help you today? Please choose an option or type your concern:\n\n"
        "🚨 *1. EMERGENCY* — Type 'Emergency' or send your location for nearest hospitals.\n\n"
        "🤒 *2. SYMPTOM CHECK* — Tell me how you feel (e.g., 'I have a fever').\n\n"
        "💉 *3. VACCINATION* — Type 'Vaccine for baby born on 1st Jan 2024'.\n\n"
        "🏥 *4. FIND HOSPITALS* — Share your location or type 'Find hospital'.\n\n"
        "📰 *5. HEALTH ALERTS* — Type 'Latest health news'.\n\n"
        "--- \n"
        "👉 *Tip:* You can speak in *Hindi, Odia, or English!* I understand all of them. 🌍"
    )

def get_ai_response(user_id: str, user_message: str) -> AIStructuredResponse:
    if user_id not in memory_cache:
        memory_cache[user_id] = []

    # Quick handle for greetings/menu requests to save tokens
    trigger_words = ["menu", "help", "hi", "hello", "नमस्ते", "hey"]
    if user_message.lower().strip() in trigger_words:
        return AIStructuredResponse(
            intent=ChatIntent.SHOW_MENU,
            reply=get_main_menu()
        )

    # ── 1. Try Gemini 2.5 Flash (Primary) ──
    if gemini_client:
        try:
            logger.info(f"--- 🧠 Calling {GEMINI_MODEL} for {user_id}... ---")

            contents = []
            for turn in memory_cache[user_id][-6:]:
                role = "model" if turn["role"] == "assistant" else "user"
                contents.append(genai_types.Content(
                    role=role,
                    parts=[genai_types.Part(text=turn["content"])]
                ))
            contents.append(genai_types.Content(
                role="user",
                parts=[genai_types.Part(text=user_message)]
            ))

            response = gemini_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=contents,
                config=genai_types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    temperature=0.7
                )
            )

            raw_text = response.text.strip()
            raw_text = re.sub(r'^```json\s*', '', raw_text)
            raw_text = re.sub(r'\s*```$', '', raw_text)
            raw_data = json.loads(raw_text, strict=False)
            
            # If AI decides to show menu
            if raw_data.get("intent") == ChatIntent.SHOW_MENU:
                raw_data["reply"] = get_main_menu()

            structured = AIStructuredResponse(**raw_data)

            memory_cache[user_id].append({"role": "user", "content": user_message})
            memory_cache[user_id].append({"role": "assistant", "content": structured.reply})
            if len(memory_cache[user_id]) > 20:
                memory_cache[user_id] = memory_cache[user_id][-20:]

            logger.info(f"--- ✅ {GEMINI_MODEL} Intent: {structured.intent.value} ---")
            return structured

        except Exception as e:
            logger.error(f"!!! {GEMINI_MODEL} Error: {e} — switching to Groq !!!")

    # ── 2. Groq Llama-3 Fallback ──
    if not groq_client:
        return AIStructuredResponse(intent=ChatIntent.GENERAL_CHAT, reply="AI service not ready.")

    logger.info(f"--- 🔁 Calling Groq Llama-3 (fallback) for {user_id}... ---")
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for turn in memory_cache[user_id][-6:]:
        messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role": "user", "content": user_message})

    try:
        chat_completion = groq_client.chat.completions.create(
            messages=messages,
            model="llama-3.3-70b-versatile",
            response_format={"type": "json_object"},
            temperature=0.7,
        )
        raw_data = json.loads(chat_completion.choices[0].message.content)
        
        if raw_data.get("intent") == ChatIntent.SHOW_MENU:
            raw_data["reply"] = get_main_menu()

        structured = AIStructuredResponse(**raw_data)

        memory_cache[user_id].append({"role": "user", "content": user_message})
        memory_cache[user_id].append({"role": "assistant", "content": raw_data.get("reply", "")})
        if len(memory_cache[user_id]) > 20:
            memory_cache[user_id] = memory_cache[user_id][-20:]

        logger.info(f"--- ✅ Groq Intent: {structured.intent.value} ---")
        return structured

    except Exception as e:
        logger.error(f"!!! Groq Error: {e} !!!")
        return AIStructuredResponse(
            intent=ChatIntent.GENERAL_CHAT,
            reply="*🩺 Arogya Mitra here.*\n\nI am listening closely. Please tell me more about how you are feeling."
        )