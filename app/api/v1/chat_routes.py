# File: app/api/v1/chat_routes.py

import logging
from fastapi import APIRouter, Depends, Form, Response
from sqlalchemy.orm import Session
from twilio.twiml.messaging_response import MessagingResponse
from typing import Optional
from datetime import datetime

from app.crud import crud_user, crud_hospitals
from app.schemas.user import UserCreate
from app.schemas.ai import ChatIntent
from app.db.session import SessionLocal
from app.services import (
    ai_service, maps_service, vaccine_service, alert_service, translation_service
)

logger = logging.getLogger(__name__)

# --- THE COMPLETE MENU TEXT ---
MENU_TEXT = """Hi! I am Ama Swasthya Sahayaka. I can help you with:

*1. Symptom Analysis* 🔎
(e.g., "I have a fever and headache")

*2. Hospital Finder* 🏥
(e.g., "find a hospital near me")

*3. Vaccination Schedule* 💉
(e.g., "vaccine schedule for baby born on 10 Jan 2025")

*4. Latest Health Alerts* 🚨
(e.g., "what are the latest health alerts?")

just ask your question directly!"""
# ------------------------------

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

router = APIRouter()

@router.post("/chat")
def handle_chat_message(
    From: str = Form(...),
    Body: Optional[str] = Form(None),
    Latitude: Optional[float] = Form(None),
    Longitude: Optional[float] = Form(None),
    db: Session = Depends(get_db)
):
    user_id = From
    user = crud_user.get_user(db, user_id=user_id)
    twiml_response = MessagingResponse()
    
    source_language = "en"
    message_body_en = Body.strip().lower() if Body else ""

    if Body:
        source_language = translation_service.detect_language(Body)
        if source_language not in ["en", "und"]:
             message_body_en = translation_service.translate_text(Body, 'en')
    
    reply_en = ""

    if not user:
        user_in = UserCreate(id=user_id)
        crud_user.create_user(db=db, user=user_in) # Corrected to use 'user'
        reply_en = MENU_TEXT
    
    elif Latitude and Longitude:
        reply_en = maps_service.find_nearby_hospitals(latitude=Latitude, longitude=Longitude)
    
    elif message_body_en in ["1", "2", "3", "4"]:
        if message_body_en == "1":
            reply_en = "You've selected Symptom Analysis. Please describe your symptoms in detail."
        elif message_body_en == "2":
            reply_en = "You've selected Hospital Finder. Please use the WhatsApp location feature to share your current location with me."
        elif message_body_en == "3":
            reply_en = "You've selected Vaccination Schedule. Please tell me the child's date of birth, for example: 'baby born on 10 January 2025'."
        elif message_body_en == "4":
            reply_en = alert_service.get_health_alerts()
    else:
        ai_response = ai_service.get_ai_response(user_id=user_id, user_message=message_body_en)

        if ai_response.intent == ChatIntent.EMERGENCY:
            logger.warning(f"EMERGENCY DETECTED: {ai_response.data.emergency_type} for User: {user_id}")
            
            # Formatted action-first emergency response
            reply_en = "🚨 *MEDICAL EMERGENCY DETECTED* 🚨\n\n"
            reply_en += "This system cannot dispatch an ambulance. Follow these steps IMMEDIATELY:\n\n"
            reply_en += "1️⃣ *DIAL 108* (Ambulance/Emergency Services) immediately.\n"
            reply_en += "2️⃣ Ensure your safety and stay calm.\n"
            
            if ai_response.data.emergency_type:
               reply_en += f"\n*Detected Situation:* {ai_response.data.emergency_type}\n"
               
            reply_en += f"\n*Guidance:* {ai_response.reply}\n\n"
            reply_en += "Reply 'find a hospital near me' to share your location for nearby centers."
            
        elif ai_response.intent == ChatIntent.SHOW_MENU:
            reply_en = MENU_TEXT
            
        elif ai_response.intent == ChatIntent.VACCINE_SCHEDULE:
            if ai_response.data.date_of_birth:
                try:
                    date_of_birth = datetime.strptime(ai_response.data.date_of_birth, "%Y-%m-%d").date()
                    reply_en = vaccine_service.calculate_vaccine_schedule(db, date_of_birth=date_of_birth)
                except Exception as e:
                    logger.error(f"Date format error: {e}")
                    reply_en = "I couldn't understand that date. Please tell me again using YYYY-MM-DD or a clear format."
            else:
                reply_en = "Please provide the exact date of birth for the vaccine schedule."
        
        elif ai_response.intent == ChatIntent.FIND_DOCTORS:
            if ai_response.data.hospital_name:
                hospital = crud_hospitals.get_hospital_by_name(db, hospital_name=ai_response.data.hospital_name)
                if hospital and hospital.doctors:
                    doctor_list = f"Here are the doctors for *{hospital.name}*:\n\n"
                    for doc in hospital.doctors:
                        doctor_list += f"🩺 *Dr. {doc.name}* ({doc.specialty})\n"
                    reply_en = doctor_list
                else:
                    reply_en = f"I couldn't find any doctors for '{ai_response.data.hospital_name}'."
            else:
                reply_en = "Please specify the name of the hospital you are looking for."
        
        elif ai_response.intent == ChatIntent.GET_ALERTS:
            reply_en = alert_service.get_health_alerts()
            
        else: # GENERAL_CHAT
            reply_en = ai_response.reply
    
    final_reply = reply_en
    if source_language not in ["en", "und"]:
        final_reply = translation_service.translate_text(reply_en, source_language)
    
    twiml_response.message(final_reply)
    return Response(content=str(twiml_response), media_type="application/xml")