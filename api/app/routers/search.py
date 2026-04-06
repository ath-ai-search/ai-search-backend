from fastapi import APIRouter
from app.models.search import SearchRequest
from app.services.search_service import execute_search

router = APIRouter()

@router.post("")
async def search_products(request: SearchRequest):
    return execute_search(request)