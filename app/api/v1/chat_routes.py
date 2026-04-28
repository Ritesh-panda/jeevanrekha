# File: app/api/v1/chat_routes.py

import os
import logging
from fastapi import APIRouter, Request, Form, Response
from typing import Optional
from twilio.twiml.messaging_response import MessagingResponse
from app.services.ai_service import get_ai_response
from app.services.voice_service import transcribe_audio, generate_speech
from app.services.maps_service import find_nearby_hospitals
from app.schemas.ai import ChatIntent
import httpx

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/chat")
async def chat_endpoint(
    request: Request,
    From: str = Form(...),
    Body: str = Form(None),
    MediaUrl0: str = Form(None),
    NumMedia: int = Form(0),
    Latitude: Optional[str] = Form(None),
    Longitude: Optional[str] = Form(None),
):
    twiml = MessagingResponse()
    user_id = From
    user_message = Body or ""

    logger.info(f"--- 📥 INCOMING from {user_id}: '{user_message}' | Lat={Latitude} Lng={Longitude} ---")

    # ─────────────────────────────────────────────
    # 1. 📍 LOCATION SHARED — Instant Hospital Search
    # ─────────────────────────────────────────────
    if Latitude and Longitude:
        logger.info(f"--- 📍 Location received: {Latitude}, {Longitude} ---")
        try:
            lat = float(Latitude)
            lng = float(Longitude)
            # Try 5km first, then widen to 10km
            hospital_list = find_nearby_hospitals(lat, lng, radius=5000)
            if "unavailable" in hospital_list.lower() or "no hospitals found" in hospital_list.lower():
                hospital_list = find_nearby_hospitals(lat, lng, radius=10000)
            reply_text = (
                f"{hospital_list}\n\n"
                f"🩺 *Tip:* Tell me your symptoms and I'll help you decide which specialist to visit."
            )
        except Exception as e:
            logger.error(f"Location Handler Error: {e}")
            reply_text = "I received your location but had trouble searching for hospitals right now. Please try again in a moment, or call *108* for emergencies."

        twiml.message(reply_text)
        return Response(content=str(twiml), media_type="text/xml")

    # ─────────────────────────────────────────────
    # 2. 🎙️ VOICE NOTE — Transcribe & Process
    # ─────────────────────────────────────────────
    is_voice = False
    if MediaUrl0 and NumMedia > 0:
        is_voice = True
        logger.info(f"--- 🎙️ Voice note received: {MediaUrl0} ---")
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(MediaUrl0)
                if resp.status_code == 200:
                    temp_audio = f"app/static/audio/input_{user_id.replace(':', '_')}.ogg"
                    os.makedirs("app/static/audio", exist_ok=True)
                    with open(temp_audio, "wb") as f:
                        f.write(resp.content)
                    user_message = await transcribe_audio(temp_audio)
                    logger.info(f"--- ✅ Transcribed: {user_message} ---")
        except Exception as e:
            logger.error(f"Voice Error: {e}")
            user_message = "I couldn't process your voice note. Please type your concern."

    # ─────────────────────────────────────────────
    # 3. 🤖 TEXT MESSAGE — AI Response
    # ─────────────────────────────────────────────
    ai_response = get_ai_response(user_id, user_message)
    reply_text = ai_response.reply or "Namaste! How can I help you today?"

    # ─────────────────────────────────────────────
    # 4. 🔀 ROUTING LOGIC
    # ─────────────────────────────────────────────
    if ai_response.intent == ChatIntent.EMERGENCY:
        reply_text = (
            f"🚨 *EMERGENCY DETECTED*\n\n"
            f"{ai_response.reply}\n\n"
            f"📍 *Share your WhatsApp location* to find the nearest emergency hospital instantly!\n"
            f"_(Tap the 📎 attachment icon → Location → Send Current Location)_"
        )
    elif ai_response.intent == ChatIntent.FIND_DOCTORS:
        reply_text = (
            f"{ai_response.reply}\n\n"
            f"📍 *To find real nearby hospitals, share your WhatsApp location!*\n"
            f"_(Tap the 📎 attachment icon → Location → Send Current Location)_"
        )

    logger.info(f"--- 📤 OUTGOING Intent={ai_response.intent.value}: {reply_text[:60]}... ---")

    # ─────────────────────────────────────────────
    # 5. 📨 SEND RESPONSE
    # ─────────────────────────────────────────────
    msg = twiml.message(reply_text)

    if is_voice:
        try:
            audio_path = await generate_speech(reply_text)
            audio_url = f"{request.base_url}static/audio/{os.path.basename(audio_path)}"
            msg.media(audio_url)
            logger.info(f"--- 🔊 Voice Response: {audio_url} ---")
        except Exception as e:
            logger.error(f"TTS Error: {e}")

    return Response(content=str(twiml), media_type="text/xml")