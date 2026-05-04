"""
=====================================================================================
📊 STATS ROUTER — Top Products APIs
=====================================================================================
This router exposes 6 endpoints for getting top products by engagement metrics.

ENDPOINTS:
  GET /products/view          → Most viewed products
  GET /products/click         → Most clicked products
  GET /products/add-to-cart   → Most added to cart
  GET /products/wishlist      → Most wished products
  GET /products/purchase      → Most purchased (best sellers)
  GET /products/trending      → Hot products (combined trending_score)

QUERY PARAMETERS (all endpoints):
  page: int (default=1)  → Page number (1-indexed)
  size: int (default=10) → Results per page (max 100)

EXAMPLE:
  GET /products/view?page=1&size=10
  GET /products/trending?page=2&size=20

RESPONSE FORMAT:
  {
    "results": [
      {
        "product_id": "6725",
        "name": "Waterpik...",
        "price": 79.99,
        "image": "https://...",
        "url": "/waterpik-...",
        "trending_score": 19,
        "stats_views": 0,
        "stats_clicks": 0,
        "stats_carts": 3,
        "stats_wishlist": 1,
        "stats_purchases": 0
      },
      ...
    ],
    "total": 60,
    "page": 1,
    "size": 10,
    "metric": "view",
    "took_ms": 45.2,
    "cached": false
  }
=====================================================================================
"""

from fastapi import APIRouter, Query
from app.services.stats_service import get_top_products_by_metric

router = APIRouter(prefix="/products", tags=["Stats"])


# =========================================================================
# 1️⃣ MOST VIEWED PRODUCTS
# =========================================================================
@router.get("/view")
async def most_viewed_products(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    size: int = Query(10, ge=1, le=100, description="Results per page (max 100)")
):
    """
    Returns products sorted by view count (most viewed first).
    
    USE CASE: 
      - "Most Viewed" homepage section
      - "Popular Right Now" carousel
    """
    return await get_top_products_by_metric("view", page=page, size=size)


# =========================================================================
# 2️⃣ MOST CLICKED PRODUCTS
# =========================================================================
@router.get("/click")
async def most_clicked_products(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    size: int = Query(10, ge=1, le=100, description="Results per page (max 100)")
):
    """
    Returns products sorted by click count (most clicked first).
    
    USE CASE:
      - "Trending Searches" section
      - High interest products
    """
    return await get_top_products_by_metric("click", page=page, size=size)


# =========================================================================
# 3️⃣ MOST ADDED TO CART
# =========================================================================
@router.get("/add-to-cart")
async def most_carted_products(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    size: int = Query(10, ge=1, le=100, description="Results per page (max 100)")
):
    """
    Returns products sorted by cart additions (most added first).
    
    USE CASE:
      - "Almost Sold Out" section
      - High intent products
    """
    return await get_top_products_by_metric("add-to-cart", page=page, size=size)


# =========================================================================
# 4️⃣ MOST WISHED PRODUCTS
# =========================================================================
@router.get("/wishlist")
async def most_wished_products(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    size: int = Query(10, ge=1, le=100, description="Results per page (max 100)")
):
    """
    Returns products sorted by wishlist count (most wished first).
    
    USE CASE:
      - "Customer Favorites" section
      - "Save for Later" inspiration
    """
    return await get_top_products_by_metric("wishlist", page=page, size=size)


# =========================================================================
# 5️⃣ MOST PURCHASED PRODUCTS (BEST SELLERS)
# =========================================================================
@router.get("/purchase")
async def most_purchased_products(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    size: int = Query(10, ge=1, le=100, description="Results per page (max 100)")
):
    """
    Returns products sorted by purchase count (best sellers first).
    
    USE CASE:
      - "Best Sellers" homepage section
      - "Top Sellers" badge products
    """
    return await get_top_products_by_metric("purchase", page=page, size=size)


# =========================================================================
# 6️⃣ TRENDING PRODUCTS (COMBINED SCORE)
# =========================================================================
@router.get("/trending")
async def trending_products(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    size: int = Query(10, ge=1, le=100, description="Results per page (max 100)")
):
    """
    Returns products sorted by combined trending score.
    
    Formula: 1 + (views×1) + (clicks×2) + (wishlist×3) + (carts×5) + (purchases×10)
    
    USE CASE:
      - "Hot Products" section
      - "What's Trending" carousel
      - Smart popular products mixing all signals
    """
    return await get_top_products_by_metric("trending", page=page, size=size)
