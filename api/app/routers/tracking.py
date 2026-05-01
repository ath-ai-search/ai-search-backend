"""
===============================================================================
FILE: main.py (tracking.py)
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
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from pydantic import BaseModel
from sqlalchemy import (
    create_engine, Column, BigInteger, String,
    Float, Integer, DateTime, Text
)
from sqlalchemy.orm import sessionmaker, declarative_base

# ============================================================
# ⚙️ CONFIG
# ============================================================

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:shubham16@localhost:5432/venue_ai"
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TrackingAPI")

# ============================================================
# 🚀 APP SETUP
# ============================================================

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with your store URL in production
    allow_methods=["*"],
    allow_headers=["*"],
)

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
# 📊 EVENT TYPE ENUM
# All event types that JS frontend can send
# ============================================================

class EventType(str, Enum):
    view = "view"
    click = "click"
    add_to_cart = "add_to_cart"
    purchase = "purchase"
    add_to_wishlist = "add_to_wishlist"
    wishlist = "wishlist"                  # JS sends "wishlist"
    search = "search"                      # JS sends "search"
    search_no_result = "search_no_result"  # JS sends "search_no_result"
    impression = "impression"              # JS sends "impression"

# ============================================================
# 🗄️ DATABASE TABLES
# ============================================================

class EventDB(Base):
    __tablename__ = "events"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    event_type = Column(String(50), index=True)
    product_id = Column(String(255), index=True)   # 255 for long URL slugs
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
    product_id = Column(String(255))
    quantity = Column(Integer, default=1)


class ProductCooccurrenceDB(Base):
    __tablename__ = "product_cooccurrence"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    product_id = Column(String(255), index=True)
    related_product_id = Column(String(255), index=True)
    score = Column(Float, default=1)


class ProductMetricsDB(Base):
    __tablename__ = "product_metrics"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    product_id = Column(String(255), index=True, unique=True)
    impressions = Column(Integer, default=0)
    views = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    carts = Column(Integer, default=0)
    purchases = Column(Integer, default=0)
    wishlist = Column(Integer, default=0)


class UserProductScoreDB(Base):
    __tablename__ = "user_product_scores"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(String(50), index=True)
    product_id = Column(String(255), index=True)
    score = Column(Float, default=0)


class WishlistDB(Base):
    __tablename__ = "wishlist"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(String(50), index=True)
    product_id = Column(String(255), index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


Base.metadata.create_all(bind=engine)

# ============================================================
# 📦 REQUEST SCHEMA
# extra = "ignore" silently drops unknown fields like priority, retries, timestamp
# ============================================================

class EventItem(BaseModel):
    event_type: EventType
    session_id: str
    product_id: Optional[str] = None
    user_id: Optional[str] = None
    query: Optional[str] = None
    position: Optional[int] = None
    source: Optional[str] = None
    value: Optional[float] = None
    timestamp: Optional[str] = None

    class Config:
        extra = "ignore"  # Ignore extra fields from JS (priority, retries, etc.)


class TrackingPayload(BaseModel):
    events: List[EventItem]

# ============================================================
# 🔁 MAIN LOGIC — runs in background after API responds
# ============================================================

def save_events_to_db(events_data: List[EventItem]):
    db = SessionLocal()

    try:
        db_events = []
        purchased_products = []
        
        # 🆕 Cache metrics + user scores within this batch to avoid duplicate inserts
        metrics_cache = {}
        ups_cache = {}

        for e in events_data:

            # 1. RAW EVENT — save every event to events table
            db_events.append(EventDB(
                event_type=e.event_type,
                product_id=e.product_id,
                user_id=e.user_id,
                session_id=e.session_id,
                query=e.query,
                position=e.position,
                value=e.value,
                source=e.source
            ))

            # Skip metrics update if no product_id
            if not e.product_id:
                continue

            # 2. PRODUCT METRICS — accumulate counts in dict (write at end with UPSERT)
            if e.product_id not in metrics_cache:
                metrics_cache[e.product_id] = {
                    'impressions': 0, 'views': 0, 'clicks': 0,
                    'carts': 0, 'purchases': 0, 'wishlist': 0
                }
            
            counts = metrics_cache[e.product_id]
            
            if e.event_type == EventType.impression:
                counts['impressions'] += 1
            elif e.event_type == EventType.view:
                counts['impressions'] += 1
                counts['views'] += 1
            elif e.event_type == EventType.click:
                counts['clicks'] += 1
            elif e.event_type == EventType.add_to_cart:
                counts['carts'] += 1
            elif e.event_type == EventType.purchase:
                counts['purchases'] += 1
                purchased_products.append(e.product_id)
            elif e.event_type in (EventType.add_to_wishlist, EventType.wishlist):
                counts['wishlist'] += 1

            # 3. USER PRODUCT SCORE — accumulate scores in dict
            if e.user_id and e.product_id:
                ups_key = (e.user_id, e.product_id)
                
                weight_map = {
                    EventType.search: 0.5,
                    EventType.impression: 0,
                    EventType.view: 1,
                    EventType.click: 2,
                    EventType.add_to_cart: 5,
                    EventType.purchase: 10,
                    EventType.add_to_wishlist: 6,
                    EventType.wishlist: 6
                }
                
                if ups_key not in ups_cache:
                    ups_cache[ups_key] = 0
                
                ups_cache[ups_key] += weight_map.get(e.event_type, 0)

            # 4. WISHLIST TABLE — save wishlist record if user is logged in
            if e.event_type in (EventType.add_to_wishlist, EventType.wishlist) and e.user_id:
                db.add(WishlistDB(
                    user_id=e.user_id,
                    product_id=e.product_id
                ))

        # 4.5 BULK UPSERT METRICS — write all accumulated counts using PostgreSQL UPSERT
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        
        if metrics_cache:
            for product_id, counts in metrics_cache.items():
                if any(v > 0 for v in counts.values()):
                    stmt = pg_insert(ProductMetricsDB).values(
                        product_id=product_id,
                        impressions=counts['impressions'],
                        views=counts['views'],
                        clicks=counts['clicks'],
                        carts=counts['carts'],
                        purchases=counts['purchases'],
                        wishlist=counts['wishlist']
                    )
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['product_id'],
                        set_={
                            'impressions': ProductMetricsDB.__table__.c.impressions + counts['impressions'],
                            'views': ProductMetricsDB.__table__.c.views + counts['views'],
                            'clicks': ProductMetricsDB.__table__.c.clicks + counts['clicks'],
                            'carts': ProductMetricsDB.__table__.c.carts + counts['carts'],
                            'purchases': ProductMetricsDB.__table__.c.purchases + counts['purchases'],
                            'wishlist': ProductMetricsDB.__table__.c.wishlist + counts['wishlist'],
                        }
                    )
                    db.execute(stmt)
        
        # 4.6 BULK UPSERT USER SCORES
        if ups_cache:
            for (user_id, product_id), score_delta in ups_cache.items():
                if score_delta > 0:
                    stmt = pg_insert(UserProductScoreDB).values(
                        user_id=user_id,
                        product_id=product_id,
                        score=score_delta
                    )
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['user_id', 'product_id'],
                        set_={
                            'score': UserProductScoreDB.__table__.c.score + score_delta
                        }
                    )
                    db.execute(stmt)
        
        # 5. ORDERS + ORDER ITEMS — created when purchase event happens
        if purchased_products:
            order = OrderDB(
                user_id=events_data[0].user_id,
                session_id=events_data[0].session_id
            )
            db.add(order)
            db.flush()  # Get order.id before adding items

            for pid in purchased_products:
                db.add(OrderItemDB(
                    order_id=order.id,
                    product_id=pid,
                    quantity=1
                ))

            # 6. CO-OCCURRENCE — track which products are bought together
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

        # Save all events to DB
        db.add_all(db_events)
        db.commit()
        logger.info(f"✅ Processed {len(events_data)} events successfully")

    except Exception as err:
        db.rollback()
        logger.error(f"❌ ERROR saving events: {err}")

    finally:
        db.close()

# ============================================================
# 🌐 API ENDPOINTS
# ============================================================

@router.post("/track")
async def track_events(payload: TrackingPayload, background_tasks: BackgroundTasks):
    if not payload.events:
        return {"status": "skipped"}

    # Process events in background so API responds immediately
    background_tasks.add_task(save_events_to_db, payload.events)

    return {
        "status": "ok",
        "message": f"{len(payload.events)} events received"
    }


@router.get("/health")
async def health():
    return {"status": "running"}


# Include router in app
app.include_router(router)
