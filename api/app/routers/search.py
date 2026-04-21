"""
=====================================================================================
🛣️ SEARCH ROUTER (API Endpoints)
=====================================================================================
This file defines all the HTTP endpoints for search features.

ENDPOINTS PROVIDED:
  POST   /search              → Main product search
  GET    /search/autocomplete → Dropdown autocomplete suggestions
  POST   /search/ai-assistant → AI chat refiner
  POST   /search/ai-welcome   → AI welcome message generator
  GET    /search/history      → Get user's recent searches
  POST   /search/history      → Save a search to history
  DELETE /search/history      → Delete a specific history item

NOTE: Routers are THIN — they just receive HTTP requests and delegate
to service functions. All business logic lives in services/.
=====================================================================================
"""

from fastapi import APIRouter, Query, Request

# Models (for request validation and response typing)
from app.models.search import (
    SearchRequest,
    AIAssistantRequest,
    AIAssistantResponse,
    AIWelcomeRequest,
    AIWelcomeResponse
)

# Import services (NEW — split into separate files!)
from app.services.search_engine import execute_search
from app.services.autocomplete import execute_autocomplete
from app.services.ai_assistant import process_ai_assistant
from app.services.ai_welcome import generate_ai_welcome
from app.services.history_service import (
    save_search_history,
    get_search_history,
    delete_search_history_item
)

# Create the router (all routes here get prefix "/search" in main.py)
router = APIRouter()


# =========================================================================
# 🔍 MAIN SEARCH ENDPOINT
# =========================================================================
@router.post("")
async def search_products(request: SearchRequest):
    """
    Main product search endpoint.
    
    RECEIVES: SearchRequest JSON body with query, page, filters, sort
    RETURNS: Search results with products, pagination, facets
    """
    return await execute_search(request)


# =========================================================================
# 🔎 AUTOCOMPLETE ENDPOINT
# =========================================================================
@router.get("/autocomplete")
async def autocomplete(q: str = Query(..., min_length=1)):
    """
    Real-time autocomplete for search dropdown.
    
    RECEIVES: ?q=search_text (query param, min 1 char)
    RETURNS: {"suggestions": [{"text": "...", "thumbnail": "..."}]}
    """
    return await execute_autocomplete(q)


# =========================================================================
# 🤖 AI ASSISTANT ENDPOINT
# =========================================================================
@router.post("/ai-assistant", response_model=AIAssistantResponse)
async def ai_assistant(request: AIAssistantRequest):
    """
    AI chat assistant — refines searches based on user's natural language.
    
    RECEIVES: {chat_message, current_state}
    RETURNS: Refined search results + AI message + suggestions
    """
    return await process_ai_assistant(request.chat_message, request.current_state)


# =========================================================================
# 👋 AI WELCOME ENDPOINT
# =========================================================================
@router.post("/ai-welcome", response_model=AIWelcomeResponse)
async def ai_welcome(request: AIWelcomeRequest):
    """
    Generates welcome message when user opens AI chat panel.
    
    RECEIVES: {current_query}
    RETURNS: {ai_message, suggestions}
    """
    return await generate_ai_welcome(request.current_query)


# =========================================================================
# 🕐 SEARCH HISTORY ENDPOINTS
# =========================================================================
# NOTE: Currently uses IP address as user_id (via request.client.host)
# TODO: Replace with proper user/session ID when auth is added

@router.get("/history")
async def get_history(request: Request):
    """
    Get user's recent search history.
    
    RETURNS: {"history": ["search1", "search2", ...]}
    """
    user_id = request.client.host  # IP address for now
    return await get_search_history(user_id)


@router.post("/history")
async def save_history(request: Request):
    """
    Save a search query to user's history.
    
    RECEIVES: {"query": "search text"}
    RETURNS: {"status": "saved" | "skipped" | "error"}
    """
    body = await request.json()
    query = body.get("query", "")
    user_id = request.client.host
    return await save_search_history(user_id, query)


@router.delete("/history")
async def delete_history(request: Request):
    """
    Delete a specific query from user's history.
    
    RECEIVES: {"query": "search text to remove"}
    RETURNS: {"status": "deleted" | "error"}
    """
    body = await request.json()
    query = body.get("query", "")
    user_id = request.client.host
    return await delete_search_history_item(user_id, query)