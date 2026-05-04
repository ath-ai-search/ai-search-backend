"""
===============================================================================
FILE: tracking.py
PURPOSE: E-commerce Event Tracking & Analytics Engine (Per-User)
===============================================================================
"""
import os
import logging
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from pydantic import BaseModel
from sqlalchemy import (
    create_engine, Column, BigInteger, String,
    Float, Integer, DateTime, Text, UniqueConstraint, Numeric, text
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
    allow_origins=["*"],
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
# 🗄️ DATABASE TABLES
# ============================================================

class EventDB(Base):
    _tablename_ = "events"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    event_type = Column(String(50), index=True)
    product_id = Column(String(255), index=True)
    visitor_id = Column(String(100), index=True)
    user_id = Column(String(100))
    session_id = Column(String(100), index=True)
    query = Column(Text)
    position = Column(Integer)
    value = Column(Float)
    source = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)


class OrderDB(Base):
    _tablename_ = "orders"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    visitor_id = Column(String(100))
    user_id = Column(String(100))
    session_id = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)


class OrderItemDB(Base):
    _tablename_ = "order_items"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    order_id = Column(BigInteger)
    product_id = Column(String(255))
    quantity = Column(Integer, default=1)


class ProductCooccurrenceDB(Base):
    _tablename_ = "product_cooccurrence"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    product_id = Column(String(255), index=True)
    related_product_id = Column(String(255), index=True)
    score = Column(Float, default=1)


class ProductMetricsDB(Base):
    _tablename_ = "product_metrics"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    visitor_id = Column(String(100), nullable=False, index=True)
    product_id = Column(String(255), nullable=False, index=True)
    impressions = Column(Integer, default=0)
    views = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    carts = Column(Integer, default=0)
    purchases = Column(Integer, default=0)
    wishlist = Column(Integer, default=0)
    trending_score = Column(Numeric, default=0)
    last_seen = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    _table_args_ = (
        UniqueConstraint('visitor_id', 'product_id', name='uq_visitor_product'),
    )


class WishlistDB(Base):
    _tablename_ = "wishlist"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(String(100), index=True)
    visitor_id = Column(String(100), index=True)
    product_id = Column(String(255), index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


Base.metadata.create_all(bind=engine)

# ============================================================
# 📦 REQUEST SCHEMA
# ============================================================

class EventItem(BaseModel):
    event_type: str
    visitor_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    product_id: Optional[str] = None
    query: Optional[str] = None
    position: Optional[int] = None
    source: Optional[str] = None
    value: Optional[float] = None
    timestamp: Optional[str] = None

    class Config:
        extra = "ignore"


class TrackingPayload(BaseModel):
    events: List[EventItem]


# ============================================================
# 🆕 HELPER: Get the identity to use for storage
# ============================================================

def get_identity(event: EventItem) -> Optional[str]:
    """
    Returns the ID to use for tracking:
    - If user logged in (user_id present): use user_id
    - Otherwise: use visitor_id
    """
    if event.user_id and event.user_id.strip() and event.user_id != "null":
        return event.user_id.strip()
    elif event.visitor_id and event.visitor_id.strip() and event.visitor_id != "null":
        return event.visitor_id.strip()
    else:
        return None


# ============================================================
# 🧮 TRENDING SCORE CALCULATOR
# ============================================================

def calculate_trending_score(views, clicks, carts, wishlist, purchases):
    return 1.0 + (
        views * 1 +
        clicks * 2 +
        wishlist * 3 +
        carts * 5 +
        purchases * 10
    )


# ============================================================
# 🔁 MAIN LOGIC — runs in background after API responds
# ============================================================

def save_events_to_db(events_data: List[EventItem]):
    db = SessionLocal()

    try:
        db_events = []
        purchased_products = []
        metrics_cache = {}

        for e in events_data:
            
            identity = get_identity(e)

            # 1. RAW EVENT
            db_events.append(EventDB(
                event_type=e.event_type,
                product_id=e.product_id,
                visitor_id=e.visitor_id,
                user_id=e.user_id,
                session_id=e.session_id,
                query=e.query,
                position=e.position,
                value=e.value,
                source=e.source
            ))

            if not e.product_id:
                continue

            if e.event_type == "impression":
                continue
            
            if not identity:
                logger.warning(f"⚠️  Event has no visitor_id or user_id, skipping metrics: {e.event_type}")
                continue

            # 2. PRODUCT METRICS
            cache_key = (identity, e.product_id)
            
            if cache_key not in metrics_cache:
                metrics_cache[cache_key] = {
                    'impressions': 0, 'views': 0, 'clicks': 0,
                    'carts': 0, 'purchases': 0, 'wishlist': 0
                }

            counts = metrics_cache[cache_key]

            if e.event_type == "view":
                counts['impressions'] += 1
                counts['views'] += 1
            elif e.event_type == "click":
                counts['clicks'] += 1
            elif e.event_type == "add_to_cart":
                counts['carts'] += 1
            elif e.event_type == "purchase":
                counts['purchases'] += 1
                purchased_products.append(e.product_id)
            elif e.event_type in ("add_to_wishlist", "wishlist"):
                counts['wishlist'] += 1

            # 3. WISHLIST TABLE
            if e.event_type in ("add_to_wishlist", "wishlist"):
                db.add(WishlistDB(
                    user_id=e.user_id,
                    visitor_id=e.visitor_id,
                    product_id=e.product_id
                ))

        # ============================================================
        # BULK UPSERT METRICS
        # ============================================================
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        if metrics_cache:
            for (identity, product_id), counts in metrics_cache.items():
                if any(v > 0 for v in counts.values()):
                    
                    new_trending = calculate_trending_score(
                        counts['views'],
                        counts['clicks'],
                        counts['carts'],
                        counts['wishlist'],
                        counts['purchases']
                    )
                    
                    stmt = pg_insert(ProductMetricsDB).values(
                        visitor_id=identity,
                        product_id=product_id,
                        impressions=counts['impressions'],
                        views=counts['views'],
                        clicks=counts['clicks'],
                        carts=counts['carts'],
                        purchases=counts['purchases'],
                        wishlist=counts['wishlist'],
                        trending_score=new_trending,
                        last_seen=datetime.utcnow()
                    )
                    
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['visitor_id', 'product_id'],
                        set_={
                            'impressions': ProductMetricsDB._table_.c.impressions + counts['impressions'],
                            'views': ProductMetricsDB._table_.c.views + counts['views'],
                            'clicks': ProductMetricsDB._table_.c.clicks + counts['clicks'],
                            'carts': ProductMetricsDB._table_.c.carts + counts['carts'],
                            'purchases': ProductMetricsDB._table_.c.purchases + counts['purchases'],
                            'wishlist': ProductMetricsDB._table_.c.wishlist + counts['wishlist'],
                            'last_seen': datetime.utcnow(),
                        }
                    )
                    db.execute(stmt)

            # Recalculate trending_score using text() wrapper
            for (identity, product_id), _ in metrics_cache.items():
                db.execute(
                    text("""
                        UPDATE product_metrics 
                        SET trending_score = 1.0 + (views * 1) + (clicks * 2) + (wishlist * 3) + (carts * 5) + (purchases * 10)
                        WHERE visitor_id = :vid AND product_id = :pid
                    """),
                    {"vid": identity, "pid": product_id}
                )

        # ============================================================
        # ORDERS + ORDER ITEMS
        # ============================================================
        if purchased_products:
            order = OrderDB(
                visitor_id=events_data[0].visitor_id,
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

            # CO-OCCURRENCE
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

        # Save all events
        db.add_all(db_events)
        db.commit()

        # Logging
        impressions_count = sum(1 for e in events_data if e.event_type == "impression")
        real_actions = len(events_data) - impressions_count

        if real_actions > 0:
            logger.info(f"✅ Processed {real_actions} real events + {impressions_count} impressions = {len(events_data)} total")
        else:
            logger.info(f"⏭️  Batch of {impressions_count} impressions only")

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