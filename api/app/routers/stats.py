"""
=====================================================================================
📊 STATS ROUTER — Consolidated APIs
=====================================================================================
1. /recommendations -> Personal Category-based (Views + Clicks)
2. /pick-up         -> Personal Intent-based (Cart + Wishlist)
3. /trending        -> Global Popularity (Purchases + Trending Score)
=====================================================================================
"""

from fastapi import APIRouter, Query
from app.services.stats_service import get_top_products_by_metric

# Removed prefix="/products" so the URL is exactly /recommendations, /pick-up, /trending
router = APIRouter(tags=["Stats"])


# =========================================================================
# 1️⃣ RECOMMENDATIONS (Personal: Views + Clicks -> Categories)
# =========================================================================
@router.get("/recommendations")
async def user_recommendations(
    visitor_id: str = Query(..., description="Browser UUID (required)"),
    user_id: str = Query(None, description="Customer ID (if logged in)"),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100)
):
    """Category-based Recommendations: Finds top categories from user views/clicks and returns matching items."""
    return await get_top_products_by_metric("recommendations", visitor_id, user_id, page, size)


# =========================================================================
# 2️⃣ PICK UP (Personal: Cart + Wishlist)
# =========================================================================
@router.get("/pick-up")
async def user_pick_up(
    visitor_id: str = Query(..., description="Browser UUID (required)"),
    user_id: str = Query(None, description="Customer ID (if logged in)"),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100)
):
    """Pick-Up: Returns products based on personal carts and wishlists."""
    return await get_top_products_by_metric("pick-up", visitor_id, user_id, page, size)


# =========================================================================
# 3️⃣ TRENDING (Global: Purchases + Trending Score)
# =========================================================================
@router.get("/trending")
async def global_trending_products(
    visitor_id: str = Query(None, description="Ignored (Global API)"),
    user_id: str = Query(None, description="Ignored (Global API)"),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100)
):
    """Trending: Returns GLOBAL trending products across all users based on purchases."""
    # We pass empty strings for identity because this API calculates globally for everyone
    return await get_top_products_by_metric("trending", visitor_id="", user_id="", page=page, size=size)