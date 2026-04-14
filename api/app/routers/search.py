from fastapi import APIRouter, Query
from app.models.search import SearchRequest
from app.services.search_service import execute_search, execute_autocomplete

router = APIRouter()

@router.post("")
async def search_products(request: SearchRequest):
    return await execute_search(request)

@router.get("/autocomplete")
async def autocomplete(q: str = Query(..., min_length=1, description="The letters the user is typing")):
    return await execute_autocomplete(q)