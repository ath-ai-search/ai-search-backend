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
    size: int = Query(20, ge=1, le=100)
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
    size: int = Query(20, ge=1, le=100)
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
    size: int = Query(20, ge=1, le=100)
):
    """Trending: Returns GLOBAL trending products across all users based on purchases."""
    # We pass empty strings for identity because this API calculates globally for everyone
    return await get_top_products_by_metric("trending", visitor_id="", user_id="", page=page, size=size)

# =========================================================================
# 4️⃣ RECOMMENDATION GRIDS (Exact Products Viewed AND Clicked)
# =========================================================================
@router.get("/recommendation-grids")
async def recommendation_grids(
    visitor_id: str = Query(..., description="Browser UUID (required)"),
    user_id: str = Query(None, description="Customer ID (if logged in)"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100)
):
    """Recommendation Grids: Returns the EXACT products the user has both viewed AND clicked."""
    return await get_top_products_by_metric("recommendation-grids", visitor_id, user_id, page, size)

# =========================================================================
# 5️⃣ CONTINUE SHOPPING (Merged: Pick-Up + Recommendation Grids)
# =========================================================================
@router.get("/continueshop")
async def continue_shopping(
    visitor_id: str = Query(..., description="Browser UUID (required)"),
    user_id: str = Query(None, description="Customer ID (if logged in)"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100)
):
    """
    Continue Shopping: Merges /pick-up (cart + wishlist) AND /recommendation-grids 
    (viewed + clicked) into a SINGLE feed. Shows EVERY product user has interacted with.
    Ordered by most-recently-touched first.
    """
    return await get_top_products_by_metric("continueshop", visitor_id, user_id, page, size)