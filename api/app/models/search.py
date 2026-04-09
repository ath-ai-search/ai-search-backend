from pydantic import BaseModel
from typing import List, Optional, Any, Dict

# ==========================================
# 📥 REQUEST MODELS (What the UI sends to us)
# ==========================================
class PriceFilter(BaseModel):
    min: Optional[float] = None
    max: Optional[float] = None

class Filters(BaseModel):
    price: Optional[PriceFilter] = None
    brand: Optional[List[str]] = None
    category: Optional[List[str]] = None
    in_stock: Optional[bool] = None

class SearchRequest(BaseModel):
    query: str
    
    # 🔥 PAGINATION CONTROLS 🔥
    page: int = 1         # The UI changes this to 2, 3, 4, etc.
    page_size: int = 24   # Keeps the grid looking nice (4 columns x 6 rows = 24)
    
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
    
    # 👇 THIS IS THE CRITICAL LINE YOU MISSED! 👇
    # It tells FastAPI that it is allowed to send the HTML to the frontend
    pagination_html: Optional[str] = ""
    
    # The actual products and filters
    results: List[Dict[str, Any]]
    facets: Dict[str, Any]
    error: Optional[str] = None