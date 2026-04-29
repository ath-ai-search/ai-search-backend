
import os

import logging

from typing import List, Optional

from datetime import datetime

from enum import Enum
 
from fastapi import APIRouter, BackgroundTasks

from pydantic import BaseModel, Field
 
from sqlalchemy import (

    create_engine, Column, BigInteger, String,

    Float, Integer, DateTime, Text

)

from sqlalchemy.orm import sessionmaker, declarative_base
 
# ============================================================

# ⚙️ CONFIG

# ============================================================
 
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/venue_ai")
 
logging.basicConfig(level=logging.INFO)

logger = logging.getLogger("TrackingAPI")
 
router = APIRouter(tags=["Tracking"])
 
# ============================================================

# 🗄️ DATABASE SETUP

# ============================================================
 
engine = create_engine(

    DATABASE_URL,

    pool_size=10,

    max_overflow=20,

    pool_timeout=30

)
 
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base = declarative_base()
 
# ============================================================

# 📊 ENUM

# ============================================================
 
class EventType(str, Enum):

    view = "view"

    click = "click"

    add_to_cart = "add_to_cart"

    purchase = "purchase"

    add_to_wishlist = "add_to_wishlist"
 
# ============================================================

# 🗄️ TABLES

# ============================================================
 
class EventDB(Base):

    __tablename__ = "events"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    event_type = Column(String(50), index=True)

    product_id = Column(String(50), index=True)

    user_id = Column(String(50))

    session_id = Column(String(100), index=True)

    query = Column(Text)

    position = Column(Integer)

    value = Column(Float)

    source = Column(String(50))

    created_at = Column(DateTime, default=datetime.utcnow)
 
 
class OrderDB(Base):

    __tablename__ = "orders"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    user_id = Column(String(50))

    session_id = Column(String(100))

    created_at = Column(DateTime, default=datetime.utcnow)
 
 
class OrderItemDB(Base):

    __tablename__ = "order_items"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    order_id = Column(BigInteger)

    product_id = Column(String(50))

    quantity = Column(Integer, default=1)
 
 
class ProductCooccurrenceDB(Base):

    __tablename__ = "product_cooccurrence"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    product_id = Column(String(50), index=True)

    related_product_id = Column(String(50), index=True)

    score = Column(Float, default=1)
 
 
class ProductMetricsDB(Base):

    __tablename__ = "product_metrics"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    product_id = Column(String(50), index=True, unique=True)

    views = Column(Integer, default=0)

    clicks = Column(Integer, default=0)

    carts = Column(Integer, default=0)

    purchases = Column(Integer, default=0)

    wishlist = Column(Integer, default=0)
 
 
class UserProductScoreDB(Base):

    __tablename__ = "user_product_scores"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    user_id = Column(String(50), index=True)

    product_id = Column(String(50), index=True)

    score = Column(Float, default=0)
 
 
class WishlistDB(Base):

    __tablename__ = "wishlist"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    user_id = Column(String(50), index=True)

    product_id = Column(String(50), index=True)

    created_at = Column(DateTime, default=datetime.utcnow)
 
 
Base.metadata.create_all(bind=engine)
 
# ============================================================

# 📦 SCHEMA

# ============================================================
 
class EventItem(BaseModel):

    event_type: EventType

    session_id: str

    product_id: Optional[str] = None

    user_id: Optional[str] = None

    query: Optional[str] = None

    position: Optional[int] = None

    value: Optional[float] = None

    source: Optional[str] = None
 
 
class TrackingPayload(BaseModel):

    events: List[EventItem]
 
# ============================================================

# 🔁 MAIN LOGIC

# ============================================================
 
def save_events_to_db(events_data: List[EventItem]):

    db = SessionLocal()
 
    try:

        db_events = []

        purchased_products = []
 
        for e in events_data:
 
            # 1. RAW EVENTS

            db_events.append(EventDB(**e.dict()))
 
            # 2. PRODUCT METRICS (UPSERT STYLE)

            metric = db.query(ProductMetricsDB).filter_by(product_id=e.product_id).first()

            if not metric:

                metric = ProductMetricsDB(product_id=e.product_id)

                db.add(metric)
 
            if e.event_type == EventType.view:

                metric.views += 1

            elif e.event_type == EventType.click:

                metric.clicks += 1

            elif e.event_type == EventType.add_to_cart:

                metric.carts += 1

            elif e.event_type == EventType.purchase:

                metric.purchases += 1

                purchased_products.append(e.product_id)

            elif e.event_type == EventType.add_to_wishlist:

                metric.wishlist += 1
 
            # 3. USER PRODUCT SCORE

            if e.user_id and e.product_id:

                ups = db.query(UserProductScoreDB).filter_by(

                    user_id=e.user_id,

                    product_id=e.product_id

                ).first()
 
                if not ups:

                    ups = UserProductScoreDB(

                        user_id=e.user_id,

                        product_id=e.product_id,

                        score=0

                    )

                    db.add(ups)
 
                weight_map = {

                    EventType.view: 1,

                    EventType.click: 2,

                    EventType.add_to_cart: 5,

                    EventType.purchase: 10,

                    EventType.add_to_wishlist: 6

                }
 
                ups.score += weight_map[e.event_type]
 
            # 4. WISHLIST

            if e.event_type == EventType.add_to_wishlist:

                db.add(WishlistDB(

                    user_id=e.user_id,

                    product_id=e.product_id

                ))
 
        # 5. ORDERS + ITEMS

        if purchased_products:

            order = OrderDB(

                user_id=events_data[0].user_id,

                session_id=events_data[0].session_id

            )

            db.add(order)

            db.flush()
 
            for pid in purchased_products:

                db.add(OrderItemDB(

                    order_id=order.id,

                    product_id=pid,

                    quantity=1

                ))
 
            # 6. COOCCURRENCE

            for i in range(len(purchased_products)):

                for j in range(i + 1, len(purchased_products)):

                    existing = db.query(ProductCooccurrenceDB).filter_by(

                        product_id=purchased_products[i],

                        related_product_id=purchased_products[j]

                    ).first()
 
                    if existing:

                        existing.score += 1

                    else:

                        db.add(ProductCooccurrenceDB(

                            product_id=purchased_products[i],

                            related_product_id=purchased_products[j],

                            score=1

                        ))
 
        # SAVE EVENTS

        db.add_all(db_events)

        db.commit()
 
        logger.info(f"✅ Processed {len(events_data)} events")
 
    except Exception as err:

        db.rollback()

        logger.error(f"❌ ERROR: {err}")
 
    finally:

        db.close()
 
# ============================================================

# 🌐 API

# ============================================================
 
@router.post("/track")

async def track_events(payload: TrackingPayload, background_tasks: BackgroundTasks):
 
    if not payload.events:

        return {"status": "skipped"}
 
    background_tasks.add_task(save_events_to_db, payload.events)
 
    return {

        "status": "ok",

        "message": f"{len(payload.events)} events received"

    }
 