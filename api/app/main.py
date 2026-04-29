"""
=====================================================================================
🚀 FASTAPI APPLICATION ENTRY POINT
=====================================================================================
This is the main entry point for the ATH AI Search API.

STARTUP FLOW:
  1. FastAPI app is created
  2. CORS middleware is configured (allows all origins)
  3. Search router is registered at /search prefix
  4. Standalone endpoints (root, autocomplete, widget) are defined

ENDPOINT STRUCTURE:
  GET  /                          → API status check
  GET  /autocomplete              → Public autocomplete (no /search prefix)
  GET  /widget/autocomplete       → Mega menu widget HTML
  POST /search                    → Main search (via router)
  GET  /search/autocomplete       → Search-prefixed autocomplete (via router)
  POST /search/ai-assistant       → AI chat (via router)
  POST /search/ai-welcome         → AI welcome (via router)
  GET|POST|DELETE /search/history → Search history (via router)
=====================================================================================
"""

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

# Import router
from app.routers import search
from app.routers import tracking  # 👈 ADD THIS LINE
# Import services we call directly from top-level routes
from app.services.autocomplete import execute_autocomplete
from app.services.widget_service import get_mega_menu_widget


# =========================================================================
# 🚀 APP INITIALIZATION
# =========================================================================
app = FastAPI(title="ATH AI Search API")

# =========================================================================
# 🌐 CORS MIDDLEWARE
# =========================================================================
# Allows frontend (any origin) to call our API
# NOTE: For production, consider restricting allow_origins to your domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # Allow any frontend domain
    allow_credentials=True,
    allow_methods=["*"],        # Allow GET, POST, PUT, DELETE, etc
    allow_headers=["*"],        # Allow any request header
)

# =========================================================================
# 📍 REGISTER ROUTERS
# =========================================================================
# All routes in routers/search.py will be prefixed with /search
# Example: @router.post("") becomes POST /search
app.include_router(search.router, prefix="/search", tags=["Search"])
# 👈 ADD THIS NEW LINE BELOW:
app.include_router(tracking.router)


# =========================================================================
# 🏠 ROOT ENDPOINT (Health Check)
# =========================================================================
@app.get("/")
async def root():
    """Simple health check to confirm API is online."""
    return {"message": "Search API is Online"}


# =========================================================================
# 🔎 TOP-LEVEL AUTOCOMPLETE (Separate from /search/autocomplete)
# =========================================================================
# NOTE: This exists in BOTH /autocomplete AND /search/autocomplete
# for backwards compatibility with different frontend versions
@app.get("/autocomplete")
async def autocomplete(q: str = Query(..., min_length=1)):
    """
    Public autocomplete endpoint (no /search prefix).
    Same behavior as /search/autocomplete.
    """
    return await execute_autocomplete(q)


# =========================================================================
# 🌐 MEGA MENU WIDGET ENDPOINT
# =========================================================================
@app.get("/widget/autocomplete")
async def mega_menu_endpoint(
    q: str = Query("", description="The search query"),
    recent: str = Query("", description="List of recent searches separated by ||")
):
    """
    Returns the mega menu dropdown HTML widget.
    
    RECEIVES:
        q: Current search query (or empty)
        recent: User's recent searches (pipe-separated: "s1||s2||s3")
    
    RETURNS: {"html": "<style>...</style><div>...products...</div>"}
    """
    return await get_mega_menu_widget(q, recent)