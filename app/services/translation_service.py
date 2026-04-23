# File: app/services/translation_service.py

import requests
import json
from app.core.config import settings

def translate_text(text: str, target_language: str):
    """Translates text using the Google Translate API with an API Key."""
    url = f"https://translation.googleapis.com/language/translate/v2?key={settings.GOOGLE_MAPS_API_KEY}"

    # The data to be sent
    payload = {
        'q': text,
        'target': target_language
    }

    try:
        # The fix is to use `json=payload` instead of `data=payload`
        response = requests.post(url, json=payload)
        response.raise_for_status()

        data = response.json()
        return data['data']['translations'][0]['translatedText']
    except Exception as e:
        print(f"--- Translation Error: {e} ---")
        return text

def detect_language(text: str):
    """Detects the language using the Google Translate API with an API Key."""
    url = f"https://translation.googleapis.com/language/translate/v2/detect?key={settings.GOOGLE_MAPS_API_KEY}"

    # The data to be sent
    payload = {
        'q': text
    }

    try:
        # The fix is to use `json=payload` here as well
        response = requests.post(url, json=payload)
        response.raise_for_status()

        data = response.json()
        return data['data']['detections'][0][0]['language']
    except Exception as e:
        print(f"--- Language Detection Error: {e} ---")
        return "en"