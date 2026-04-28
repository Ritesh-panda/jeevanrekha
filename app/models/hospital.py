from sqlalchemy import Column, String, Integer, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base

class Hospital(Base):
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    city = Column(String)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    doctors = relationship("Doctor", back_populates="hospital")

class Doctor(Base):
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    specialty = Column(String)
    hospital_id = Column(Integer, ForeignKey("hospitals.id"))
    hospital = relationship("Hospital", back_populates="doctors")