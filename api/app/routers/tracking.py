import os
import logging
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, BigInteger, String, Float, Integer, DateTime, Text
from sqlalchemy.orm import sessionmaker, declarative_base

# =====================================================================
# ⚙️ CONFIGURATION & SETUP
# =====================================================================
# Hardcoded for local testing only! Do not upload this to a public GitHub repo.
DATABASE_URL = "postgresql://postgres:shubham16@localhost:5432/venue_ai"

logger = logging.getLogger("TrackerAPI")

# Create a Router instead of a full app
router = APIRouter(tags=["Tracking"])

# =====================================================================
# 🗄️ DATABASE MODELS (SQLAlchemy)
# =====================================================================
engine = create_engine(DATABASE_URL, pool_size=20, max_overflow=0)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class EventDB(Base):
    __tablename__ = "events"

    id = Column(BigInteger, primary_key=True, index=True)
    event_type = Column(String(50), nullable=False)
    product_id = Column(String(50), nullable=True)
    user_id = Column(String(50), nullable=True)
    session_id = Column(String(100), nullable=False)
    query = Column(Text, nullable=True)
    position = Column(Integer, nullable=True)
    value = Column(Float, nullable=True)
    source = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

# =====================================================================
# 📦 PYDANTIC SCHEMAS (Validation)
# =====================================================================
class EventItem(BaseModel):
    event_type: str
    session_id: str
    product_id: Optional[str] = None
    user_id: Optional[str] = None
    query: Optional[str] = None
    position: Optional[int] = None
    value: Optional[float] = None
    source: Optional[str] = None
    timestamp: Optional[str] = None 

class TrackingPayload(BaseModel):
    events: List[EventItem]

# =====================================================================
# 🚀 BACKGROUND WORKER
# =====================================================================
def save_events_to_db(events_data: List[EventItem]):
    db = SessionLocal()
    try:
        db_events = []
        for e in events_data:
            new_event = EventDB(
                event_type=e.event_type,
                product_id=e.product_id,
                user_id=e.user_id,
                session_id=e.session_id,
                query=e.query,
                position=e.position,
                value=e.value,
                source=e.source
            )
            db_events.append(new_event)
        
        db.bulk_save_objects(db_events)
        db.commit()
        logger.info(f"✅ Successfully saved {len(db_events)} events to PostgreSQL.")
        
    except Exception as err:
        db.rollback()
        logger.error(f"❌ Failed to save events: {err}")
    finally:
        db.close()

# =====================================================================
# 🌐 API ENDPOINT
# =====================================================================
@router.post("/track")
async def track_events(payload: TrackingPayload, background_tasks: BackgroundTasks):
    if not payload.events:
        return {"status": "skipped", "message": "No events provided."}

    background_tasks.add_task(save_events_to_db, payload.events)
    
    return {"status": "ok", "message": f"Processing {len(payload.events)} events."}