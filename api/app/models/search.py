from pydantic import BaseModel
from typing import List, Optional, Any, Dict

# =========================================================================
# 📥 REQUEST MODELS
# =========================================================================

class PriceFilter(BaseModel):
    min: Optional[float] = None
    max: Optional[float] = None

class Filters(BaseModel):
    price: Optional[PriceFilter] = None
    category: Optional[List[str]] = None
    in_stock: Optional[bool] = None
    color: Optional[List[str]] = None
    brand: Optional[List[str]] = None # Kept optional to prevent 422 cache errors
    gender: Optional[List[str]] = None # Kept optional to prevent 422 cache errors

class SearchRequest(BaseModel):
    query: str
    page: int = 1
    page_size: int = 25
    filters: Optional[Filters] = None
    sort: str = "relevance"

class AIAssistantRequest(BaseModel):
    chat_message: str
    current_state: SearchRequest

# =========================================================================
# 📤 RESPONSE MODELS
# =========================================================================

class SearchResponse(BaseModel):
    total_results: int
    total_pages: int
    current_page: int
    pagination_html: Optional[str] = ""
    results: List[Dict[str, Any]]
    facets: Dict[str, Any]
    error: Optional[str] = None

class AIAssistantResponse(SearchResponse):
    ai_message: Optional[str] = ""
    updated_query: Optional[str] = None
    updated_filters: Optional[Dict[str, Any]] = None