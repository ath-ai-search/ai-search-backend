"""
===============================================================================
FILE: tracking.py
PURPOSE: E-commerce Event Tracking & Analytics Engine
===============================================================================
This file acts as the "brain" for tracking user behavior on the website. 
When a user views, clicks, adds to cart, or purchases a product, the frontend 
sends that data to the `/track` API endpoint in this file. 

What this file does automatically in the background:
1. RAW EVENTS: Saves a permanent record of every single action a user takes.
2. PRODUCT METRICS: Updates the counters for total views, clicks, carts, and 
   purchases for each product.
3. USER SCORES: Calculates an affinity score (how much a user likes a product) 
   by adding points based on their actions (e.g., purchase = +10, view = +1).
4. ORDERS: If the event is a 'purchase', it automatically generates an Order 
   record and links the purchased Order Items.
5. CO-OCCURRENCE: Tracks which products are purchased together to help build 
   "Frequently Bought Together" recommendations in the future.
===============================================================================
"""
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

DATABASE_URL = "postgresql://postgres:shubham16@localhost:5432/venue_ai"
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
    # search="search"

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
    # search=Column(Integer, default=0)        # ✅ NEW COLUMN
    impressions=Column(Integer, default=0)   # ✅ NEW
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
            # 1. RAW EVENTS (no change)
            db_events.append(EventDB(**e.dict()))

            # 🚨 IMPORTANT FIX: skip metrics if no product_id
            if not e.product_id:
                continue

            # 2. PRODUCT METRICS (UPSERT)
            metric = db.query(ProductMetricsDB).filter_by(product_id=e.product_id).first()
            if not metric:
                # 🚨 FIX 1: Explicitly set the starting numbers to 0 to prevent the NoneType crash!
                metric = ProductMetricsDB(
                    product_id=e.product_id,
                    impressions=0,
                    views=0,
                    clicks=0,
                    carts=0,
                    purchases=0,
                    wishlist=0
                )
                db.add(metric)

            # ✅ UPDATED METRIC LOGIC
            if e.event_type == EventType.view:
                metric.impressions += 1   # NEW
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

            # 3. USER PRODUCT SCORE (SAFE)
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
                    # EventType.search: 0.5, # 🚨 FIX 3: Give searches a small score weight!
                    EventType.view: 1,
                    EventType.click: 2,
                    EventType.add_to_cart: 5,
                    EventType.purchase: 10,
                    EventType.add_to_wishlist: 6
                }

                ups.score += weight_map.get(e.event_type, 0)

            # 4. WISHLIST (SAFE FIX)
            if e.event_type == EventType.add_to_wishlist and e.user_id:
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