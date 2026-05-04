"""
=====================================================================================
📊 STATS ROUTER — Personal Top Products APIs (Per User)
=====================================================================================
6 endpoints that return products specific to each user.

LOGIC:
  - visitor_id is REQUIRED (always sent by frontend)
  - user_id is OPTIONAL (only if user is logged in)
  - If user_id provided → query by user_id (cross-device)
  - If only visitor_id → query by visitor_id (browser-specific)

ENDPOINTS:
  GET /products/view?visitor_id=...&user_id=...
  GET /products/click?visitor_id=...&user_id=...
  GET /products/add-to-cart?visitor_id=...&user_id=...
  GET /products/wishlist?visitor_id=...&user_id=...
  GET /products/purchase?visitor_id=...&user_id=...
  GET /products/trending?visitor_id=...&user_id=...

OPTIONAL PARAMS:
  page: int (default=1)
  size: int (default=10, max=100)
=====================================================================================
"""

from fastapi import APIRouter, Query
from app.services.stats_service import get_top_products_by_metric

router = APIRouter(prefix="/products", tags=["Stats"])


# =========================================================================
# 1️⃣ MOST VIEWED PRODUCTS (per user)
# =========================================================================
@router.get("/view")
async def user_viewed_products(
    visitor_id: str = Query(..., description="Browser UUID (required)"),
    user_id: str = Query(None, description="Customer ID (if logged in)"),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100)
):
    """Returns products THIS user viewed."""
    return await get_top_products_by_metric(
        metric="view",
        visitor_id=visitor_id,
        user_id=user_id,
        page=page,
        size=size
    )


# =========================================================================
# 2️⃣ MOST CLICKED PRODUCTS (per user)
# =========================================================================
@router.get("/click")
async def user_clicked_products(
    visitor_id: str = Query(..., description="Browser UUID (required)"),
    user_id: str = Query(None, description="Customer ID (if logged in)"),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100)
):
    """Returns products THIS user clicked."""
    return await get_top_products_by_metric(
        metric="click",
        visitor_id=visitor_id,
        user_id=user_id,
        page=page,
        size=size
    )


# =========================================================================
# 3️⃣ MOST ADDED TO CART (per user)
# =========================================================================
@router.get("/add-to-cart")
async def user_carted_products(
    visitor_id: str = Query(..., description="Browser UUID (required)"),
    user_id: str = Query(None, description="Customer ID (if logged in)"),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100)
):
    """Returns products THIS user added to cart."""
    return await get_top_products_by_metric(
        metric="add-to-cart",
        visitor_id=visitor_id,
        user_id=user_id,
        page=page,
        size=size
    )


# =========================================================================
# 4️⃣ MOST WISHED PRODUCTS (per user)
# =========================================================================
@router.get("/wishlist")
async def user_wishlisted_products(
    visitor_id: str = Query(..., description="Browser UUID (required)"),
    user_id: str = Query(None, description="Customer ID (if logged in)"),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100)
):
    """Returns products THIS user wishlisted."""
    return await get_top_products_by_metric(
        metric="wishlist",
        visitor_id=visitor_id,
        user_id=user_id,
        page=page,
        size=size
    )


# =========================================================================
# 5️⃣ MOST PURCHASED PRODUCTS (per user)
# =========================================================================
@router.get("/purchase")
async def user_purchased_products(
    visitor_id: str = Query(..., description="Browser UUID (required)"),
    user_id: str = Query(None, description="Customer ID (if logged in)"),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100)
):
    """Returns products THIS user purchased."""
    return await get_top_products_by_metric(
        metric="purchase",
        visitor_id=visitor_id,
        user_id=user_id,
        page=page,
        size=size
    )


# =========================================================================
# 6️⃣ TRENDING PRODUCTS (per user)
# =========================================================================
@router.get("/trending")
async def user_trending_products(
    visitor_id: str = Query(..., description="Browser UUID (required)"),
    user_id: str = Query(None, description="Customer ID (if logged in)"),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100)
):
    """
    Returns THIS user's trending products (combined score).
    
    Score Formula:
      trending_score = 1 + (views×1) + (clicks×2) + (wishlist×3) + (carts×5) + (purchases×10)
    """
    return await get_top_products_by_metric(
        metric="trending",
        visitor_id=visitor_id,
        user_id=user_id,
        page=page,
        size=size
    )
