from fastapi import APIRouter, Query
from app.models.search import SearchRequest, AIQuery
from app.services.search_service import execute_search, execute_autocomplete, execute_ai_search

router = APIRouter()

# 1️⃣ MAIN SEARCH (Returns flat list of results with filters & pagination)
@router.post("")
async def search_products(request: SearchRequest):
    return await execute_search(request)

# 2️⃣ SIR'S MEGA MENU SEARCH (Returns JSON grouped by categories)
@router.post("/ai-search")
async def ai_search(q: AIQuery):
    return await execute_ai_search(q.query)

# 3️⃣ FAST AUTOCOMPLETE (Keeps keystroke predictions fast)
@router.get("/autocomplete")
async def autocomplete(q: str = Query(..., min_length=1, description="The letters the user is typing")):
    """
    Ultra-fast endpoint for search bar suggestions (Amazon style).
    """
    return await execute_autocomplete(q)