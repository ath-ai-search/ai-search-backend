from fastapi import APIRouter, Query
from app.models.search import SearchRequest
# ✅ ADDED: Import the new execute_autocomplete function
from app.services.search_service import execute_search, execute_autocomplete

router = APIRouter()

@router.post("")
async def search_products(request: SearchRequest):
    # ✅ MUST use 'await' because service is now 'async'
    return await execute_search(request)

# ==========================================
# ✅ ADDED: The new Autocomplete Endpoint
# ==========================================
@router.get("/autocomplete")
async def autocomplete(q: str = Query(..., min_length=1, description="The letters the user is typing")):
    """
    Ultra-fast endpoint for search bar suggestions (Amazon style).
    """
    return await execute_autocomplete(q)