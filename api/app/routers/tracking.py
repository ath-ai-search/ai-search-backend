"""
===============================================================================
FILE: tracking.py
PURPOSE: E-commerce Event Tracking & Analytics Engine (Per-User)
===============================================================================
🆕 PERSONALIZED TRACKING:
   - product_metrics now stores PER-USER counts (not global)
   - Uses visitor_id as primary identifier
   - If user logged in: stores user_id in visitor_id field
   - If anonymous: stores UUID in visitor_id field

What this file does:
1. RAW EVENTS: Saves every action to events table
2. PRODUCT METRICS: Updates per-user counters in product_metrics
3. USER SCORES: Updates user_product_scores
4. ORDERS: Creates order records on purchase
5. CO-OCCURRENCE: Tracks products bought together
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
    Float, Integer, DateTime, Text, UniqueConstraint, Numeric
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
    __tablename__ = "events"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    event_type = Column(String(50), index=True)
    product_id = Column(String(255), index=True)
    visitor_id = Column(String(100), index=True)  # 🆕 NEW
    user_id = Column(String(100))
    session_id = Column(String(100), index=True)
    query = Column(Text)
    position = Column(Integer)
    value = Column(Float)
    source = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)


class OrderDB(Base):
    __tablename__ = "orders"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    visitor_id = Column(String(100))  # 🆕 NEW
    user_id = Column(String(100))
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
    """
    🆕 MODIFIED: Now stores PER-USER counts
    Primary key changed from product_id to (visitor_id, product_id)
    """
    __tablename__ = "product_metrics"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    visitor_id = Column(String(100), nullable=False, index=True)  # 🆕 NEW
    product_id = Column(String(255), nullable=False, index=True)
    impressions = Column(Integer, default=0)
    views = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    carts = Column(Integer, default=0)
    purchases = Column(Integer, default=0)
    wishlist = Column(Integer, default=0)
    trending_score = Column(Numeric, default=0)  # 🆕 NEW
    last_seen = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('visitor_id', 'product_id', name='uq_visitor_product'),
    )


class UserProductScoreDB(Base):
    __tablename__ = "user_product_scores"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(String(100), index=True)
    product_id = Column(String(255), index=True)
    score = Column(Float, default=0)

    __table_args__ = (
        UniqueConstraint('user_id', 'product_id', name='uq_user_product'),
    )


class WishlistDB(Base):
    __tablename__ = "wishlist"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(String(100), index=True)
    visitor_id = Column(String(100), index=True)  # 🆕 NEW
    product_id = Column(String(255), index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


Base.metadata.create_all(bind=engine)

# ============================================================
# 📦 REQUEST SCHEMA
# ============================================================

class EventItem(BaseModel):
    event_type: str
    visitor_id: Optional[str] = None  # 🆕 NEW: from JS
    user_id: Optional[str] = None      # If logged in
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
    - If user is logged in (user_id present): use user_id
    - If user is anonymous (only visitor_id): use visitor_id
    - If neither: returns None (skip tracking)
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
    """Same formula as pipeline.py"""
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

        # Cache metrics + user scores within this batch
        # 🆕 Key changed from product_id to (identity, product_id)
        metrics_cache = {}
        ups_cache = {}

        weight_map = {
            "search": 0.5,
            "impression": 0,
            "view": 1,
            "click": 2,
            "add_to_cart": 5,
            "purchase": 10,
            "add_to_wishlist": 6,
            "wishlist": 6
        }

        for e in events_data:
            
            # 🆕 Determine identity (user_id if logged in, else visitor_id)
            identity = get_identity(e)

            # 1. RAW EVENT — save every event to events table
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

            # Skip if no product_id
            if not e.product_id:
                continue

            # Skip impression events
            if e.event_type == "impression":
                continue
            
            # 🆕 Skip if no identity (no visitor_id AND no user_id)
            if not identity:
                logger.warning(f"⚠️  Event has no visitor_id or user_id, skipping metrics: {e.event_type}")
                continue

            # 2. PRODUCT METRICS — accumulate per-identity counts
            # 🆕 Key is now (identity, product_id)
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

            # 3. USER PRODUCT SCORE (only for logged in users)
            if e.user_id and e.product_id:
                ups_key = (e.user_id, e.product_id)

                if ups_key not in ups_cache:
                    ups_cache[ups_key] = 0

                ups_cache[ups_key] += weight_map.get(e.event_type, 0)

            # 4. WISHLIST TABLE
            if e.event_type in ("add_to_wishlist", "wishlist"):
                db.add(WishlistDB(
                    user_id=e.user_id,
                    visitor_id=e.visitor_id,
                    product_id=e.product_id
                ))

        # ============================================================
        # 4.5 BULK UPSERT METRICS — write per-visitor counts
        # ============================================================
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        if metrics_cache:
            for (identity, product_id), counts in metrics_cache.items():
                if any(v > 0 for v in counts.values()):
                    
                    # Calculate trending_score for this row
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
                    
                    # 🆕 Conflict on (visitor_id, product_id) instead of just product_id
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['visitor_id', 'product_id'],
                        set_={
                            'impressions': ProductMetricsDB.__table__.c.impressions + counts['impressions'],
                            'views': ProductMetricsDB.__table__.c.views + counts['views'],
                            'clicks': ProductMetricsDB.__table__.c.clicks + counts['clicks'],
                            'carts': ProductMetricsDB.__table__.c.carts + counts['carts'],
                            'purchases': ProductMetricsDB.__table__.c.purchases + counts['purchases'],
                            'wishlist': ProductMetricsDB.__table__.c.wishlist + counts['wishlist'],
                            'last_seen': datetime.utcnow(),
                            # Trending score will be recalculated by trigger or we update separately
                        }
                    )
                    db.execute(stmt)

            # 🆕 Recalculate trending_score for all updated rows
            # (Using SQL to compute from final values after upsert)
            for (identity, product_id), _ in metrics_cache.items():
                db.execute(
                    """
                    UPDATE product_metrics 
                    SET trending_score = 1.0 + (views * 1) + (clicks * 2) + (wishlist * 3) + (carts * 5) + (purchases * 10)
                    WHERE visitor_id = :vid AND product_id = :pid
                    """,
                    {"vid": identity, "pid": product_id}
                )

        # ============================================================
        # 4.6 BULK UPSERT USER SCORES (only for logged in users)
        # ============================================================
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

        # ============================================================
        # 5. ORDERS + ORDER ITEMS
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

            # 6. CO-OCCURRENCE
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
