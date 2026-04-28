# File: app/services/hospital_service.py

from sqlalchemy.orm import Session
from sqlalchemy import func
from math import radians, cos, sin, asin, sqrt

from app.models.hospital import Hospital


def _haversine(lat1, lon1, lat2, lon2):
    """Calculate the great-circle distance (km) between two points."""
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 6371 * 2 * asin(sqrt(a))


def get_nearest_hospitals(db: Session, latitude: float, longitude: float):
    """
    Finds the 3 nearest hospitals to the given latitude and longitude.
    Uses in-memory Haversine distance (no PostGIS required).
    """
    hospitals = db.query(Hospital).filter(
        Hospital.latitude.isnot(None),
        Hospital.longitude.isnot(None),
    ).all()

    hospitals_with_dist = [
        (h, _haversine(latitude, longitude, h.latitude, h.longitude))
        for h in hospitals
    ]
    hospitals_with_dist.sort(key=lambda x: x[1])

    return [h for h, _ in hospitals_with_dist[:3]]