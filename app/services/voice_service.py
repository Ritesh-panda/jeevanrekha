# File: app/services/voice_service.py

import os
import logging
from gtts import gTTS
from groq import Groq
from app.core.config import settings

logger = logging.getLogger(__name__)

# Initialize Groq client safely
client = None
try:
    if settings.GROQ_API_KEY:
        client = Groq(api_key=settings.GROQ_API_KEY)
except Exception as e:
    logger.warning(f"Failed to initialize Groq client in voice_service: {e}")

async def transcribe_audio(audio_path: str) -> str:
    """
    Transcribe audio using Groq's Whisper-large-v3 (FREE Tier)
    """
    if not client:
        logger.error("Groq client is not initialized. Cannot transcribe audio.")
        return "Transcribing failed (Groq client not configured)."
    try:
        with open(audio_path, "rb") as file:
            transcription = client.audio.transcriptions.create(
                file=(os.path.basename(audio_path), file.read()),
                model="whisper-large-v3",
                prompt="The user is speaking about health concerns in India.",
                response_format="text",
            )
            return transcription
    except Exception as e:
        logger.error(f"Groq Transcription Error: {e}")
        return ""

async def generate_speech(text: str) -> str:
    """
    Generate speech using gTTS (Google Text-to-Speech - FREE)
    """
    try:
        tts = gTTS(text=text, lang='en', tld='co.in') # Indian accent
        output_filename = f"response_{hash(text) % 10000}.mp3"
        output_path = os.path.join("app/static/audio", output_filename)
        os.makedirs("app/static/audio", exist_ok=True)
        tts.save(output_path)
        return output_path
    except Exception as e:
        logger.error(f"gTTS Error: {e}")
        raise e
