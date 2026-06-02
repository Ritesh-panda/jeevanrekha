from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# The engine manages a pool of connections to the database.
db_url = settings.DATABASE_URL or "sqlite:///./local.db"
connect_args = {}
if db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(db_url, pool_pre_ping=True, connect_args=connect_args)

# The SessionLocal class is a "factory" for creating new database sessions.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)