from pydantic import BaseModel
from typing import List, Optional, Any, Dict

# ==========================================
# 📥 REQUEST MODELS (What the UI sends to us)
# ==========================================
# ✅ ADDED: The model for your sir's new /ai-search endpoint
class AIQuery(BaseModel):
    query: str

class PriceFilter(BaseModel):
    min: Optional[float] = None
    max: Optional[float] = None

class Filters(BaseModel):
    price: Optional[PriceFilter] = None
    brand: Optional[List[str]] = None
    category: Optional[List[str]] = None
    in_stock: Optional[bool] = None
    
    # 🟢 NEW: Added to support the new UI sidebar arrays
    color: Optional[List[str]] = None
    gender: Optional[List[str]] = None
    size: Optional[List[str]] = None

class SearchRequest(BaseModel):
    query: str
    
    # 🔥 PAGINATION CONTROLS 🔥
    page: int = 1        # The UI changes this to 2, 3, 4, etc.
    page_size: int = 25  # Keeps the grid looking nice
    
    filters: Optional[Filters] = None
    sort: str = "relevance"


# ==========================================
# 📤 RESPONSE MODELS (What we send to the UI)
# ==========================================
class SearchResponse(BaseModel):
    # 🔥 PAGINATION DATA FOR THE UI TO DRAW BUTTONS 🔥
    total_results: int
    total_pages: int
    current_page: int
    
    pagination_html: Optional[str] = ""
    
    # The actual products and filters
    results: List[Dict[str, Any]]
    facets: Dict[str, Any]
    error: Optional[str] = None