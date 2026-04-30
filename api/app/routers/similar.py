from fastapi import APIRouter
from app.services.similar_service import (
    get_embedding, 
    ai_search, 
    fallback_search, 
    format_response
)

router = APIRouter(tags=["Similar Products"])

# ==========================
# API 1: AI SIMILAR PRODUCTS
# ==========================
@router.get("/ai-similar-products")
def ai_similar_products(
    product_id: str,
    name: str = "",
    description: str = "",
    category_id: str = "",
    page: int = 1,
    size: int = 8
):
    try:
        # ✅ Fetch stored embedding from AWS OpenSearch
        vector = get_embedding(product_id)

        if not vector:
            raise Exception("No embedding found")

        # ✅ Run Vector Search
        data = ai_search(vector, product_id, category_id, page, size)
        results = format_response(data)

        # ✅ Fallback to text search if AI returns 0 results
        if not results:
            fallback_data = fallback_search(product_id, category_id, page, size)
            results = format_response(fallback_data)

        return {"results": results}

    except Exception as e:
        return {"results": [], "error": str(e)}

# ==========================
# API 2: FALLBACK ONLY
# ==========================
@router.get("/similar-products")
def similar_products(
    product_id: str,
    category_id: str = "",
    page: int = 1,
    size: int = 8
):
    data = fallback_search(product_id, category_id, page, size)
    return {"results": format_response(data)}