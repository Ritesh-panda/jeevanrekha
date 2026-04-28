# File: seed_database.py

from app.db.session import SessionLocal
from app.models.hospital import Hospital, Doctor

# Get a database session
db = SessionLocal()

def seed_data():
    """
    Populates the database with initial hospital and doctor data.
    """
    print("--- Seeding database with initial data... ---")

    # Clear existing data to avoid duplicates
    db.query(Doctor).delete()
    db.query(Hospital).delete()
    db.commit()
    print("--- Cleared existing hospital and doctor data. ---")

    # --- Hospital Data for Odisha ---
    hospitals_data = [
        {
            "name": "AIIMS Bhubaneswar",
            "city": "Bhubaneswar",
            "latitude": 20.2437,
            "longitude": 85.7977,
            "doctors": [
                {"name": "Dr. Gitanjali Batmanabane", "specialty": "General Medicine"},
                {"name": "Dr. Ashok Mahapatra", "specialty": "Neurosurgery"}
            ]
        },
        {
            "name": "Capital Hospital",
            "city": "Bhubaneswar",
            "latitude": 20.2724,
            "longitude": 85.8236,
            "doctors": [
                {"name": "Dr. Laxmidhar Sahoo", "specialty": "General Medicine"},
                {"name": "Dr. P. K. Mohanty", "specialty": "Cardiology"}
            ]
        },
        {
            "name": "SCB Medical College and Hospital",
            "city": "Cuttack",
            "latitude": 20.4727,
            "longitude": 85.8858,
            "doctors": [
                {"name": "Dr. Jayant Panda", "specialty": "General Medicine"},
                {"name": "Dr. Sidhartha Das", "specialty": "Pediatrics"}
            ]
        },
        {
            "name": "AMRI Hospital",
            "city": "Bhubaneswar",
            "latitude": 20.3005,
            "longitude": 85.8282,
            "doctors": [
                {"name": "Dr. Anjan Kumar Panda", "specialty": "Oncology"},
                {"name": "Dr. J. K. Padhi", "specialty": "Neurology"}
            ]
        }
    ]

    for h_data in hospitals_data:
        # Create the Hospital object
        hospital = Hospital(
            name=h_data["name"],
            city=h_data["city"],
            latitude=h_data["latitude"],
            longitude=h_data["longitude"]
        )
        db.add(hospital)
        db.commit() # Commit to get the hospital.id for the doctors

        # Create and add the associated Doctor objects
        for d_data in h_data["doctors"]:
            doctor = Doctor(
                name=d_data["name"],
                specialty=d_data["specialty"],
                hospital_id=hospital.id
            )
            db.add(doctor)

    # Commit all the new doctors
    db.commit()
    print("--- New data has been seeded successfully! ---")

if __name__ == "__main__":
    seed_data()
    db.close()