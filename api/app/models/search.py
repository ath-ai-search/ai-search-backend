from pydantic import BaseModel
from typing import List, Optional

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
    page: int = 1
    page_size: int = 20
    filters: Optional[Filters] = None
    sort: str = "relevance"