# File: app/services/maps_service.py

import requests
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

def find_nearby_hospitals(latitude: float, longitude: float, radius: int = 5000):
    """
    Finds nearby hospitals using Google Places API (New).
    Falls back to OpenStreetMap if API key is missing or fails.
    """
    if settings.GOOGLE_MAPS_API_KEY and settings.GOOGLE_MAPS_API_KEY != "YOUR_MAPS_API_KEY_HERE":
        return _find_via_google(latitude, longitude, radius)
    else:
        logger.warning("No Google Maps key found. Using OpenStreetMap fallback.")
        return _find_via_osm(latitude, longitude, radius)


def _find_via_google(latitude: float, longitude: float, radius: int):
    """Google Places API (New) — Nearby Search"""
    url = "https://places.googleapis.com/v1/places:searchNearby"
    
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": settings.GOOGLE_MAPS_API_KEY,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.nationalPhoneNumber,places.rating,places.googleMapsUri,places.currentOpeningHours"
    }
    
    body = {
        "includedTypes": ["hospital"],
        "maxResultCount": 5,
        "locationRestriction": {
            "circle": {
                "center": {
                    "latitude": latitude,
                    "longitude": longitude
                },
                "radius": float(radius)
            }
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=body, timeout=10)
        response.raise_for_status()
        data = response.json()
        places = data.get("places", [])
        
        if not places:
            logger.warning("Google Places returned no results. Trying OSM fallback.")
            return _find_via_osm(latitude, longitude, radius)
        
        reply = "🏥 *Here are hospitals near you:*\n\n"
        
        for place in places:
            name = place.get("displayName", {}).get("text", "Unknown Hospital")
            address = place.get("formattedAddress", "Address not available")
            phone = place.get("nationalPhoneNumber", "Phone not available")
            rating = place.get("rating", None)
            maps_link = place.get("googleMapsUri", "")
            is_open = place.get("currentOpeningHours", {}).get("openNow", None)
            
            open_status = ""
            if is_open is True:
                open_status = "🟢 Open Now"
            elif is_open is False:
                open_status = "🔴 Currently Closed"
            
            reply += f"🏥 *{name}*\n"
            reply += f"📍 _{address}_\n"
            reply += f"📞 {phone}\n"
            if rating:
                reply += f"⭐ Rating: {rating}/5\n"
            if open_status:
                reply += f"{open_status}\n"
            if maps_link:
                reply += f"🗺️ {maps_link}\n"
            reply += "\n"
        
        reply += "_Powered by Google Maps_ 🗺️"
        logger.info(f"--- ✅ Google Places found {len(places)} hospitals ---")
        return reply

    except Exception as e:
        logger.error(f"Google Places API Error: {e}. Falling back to OSM.")
        return _find_via_osm(latitude, longitude, radius)


def _find_via_osm(latitude: float, longitude: float, radius: int):
    """OpenStreetMap Overpass API — Free fallback"""
    overpass_url = "https://overpass-api.de/api/interpreter"
    query = f"""
    [out:json];
    (
      node["amenity"="hospital"](around:{radius},{latitude},{longitude});
      way["amenity"="hospital"](around:{radius},{latitude},{longitude});
    );
    out center;
    """
    try:
        response = requests.get(overpass_url, params={'data': query}, timeout=15)
        response.raise_for_status()
        elements = response.json().get('elements', [])

        if not elements:
            return "⚠️ No hospitals found within 5km of your location. Try calling *108* for emergency assistance."

        reply = "🏥 *Nearby Hospitals:*\n\n"
        for element in elements[:4]:
            tags = element.get('tags', {})
            name = tags.get('name', 'Unnamed Hospital')
            address = tags.get('addr:full') or f"{tags.get('addr:street', '')} {tags.get('addr:city', '')}".strip() or "Address info not available"
            phone = tags.get('phone') or tags.get('contact:phone') or "Phone not available"
            
            reply += f"🏥 *{name}*\n"
            reply += f"📍 _{address}_\n"
            reply += f"📞 {phone}\n\n"

        return reply

    except Exception as e:
        logger.error(f"OSM Fallback Error: {e}")
        return "⚠️ Hospital search is temporarily unavailable. In an emergency, please call *108* immediately."