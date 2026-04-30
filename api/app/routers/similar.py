from fastapi import APIRouter
from app.services.similar_service import (
    get_embedding, 
    ai_search, 
    fallback_search, 
    format_response
)

router = APIRouter(tags=["Similar Products"])

@router.get("/ai-similar-products")
def ai_similar_products(
    product_id: str,
    category_id: str = "",
    page: int = 1,
    size: int = 8
):
    try:
        vector = get_embedding(product_id)
        if not vector:
            raise Exception("No embedding found")

        data = ai_search(vector, product_id, category_id, page, size)
        results = format_response(data)

        if not results:
            fallback_data = fallback_search(product_id, category_id, page, size)
            results = format_response(fallback_data)

        return {"results": results}
    except Exception as e:
        return {"results": [], "error": str(e)}

@router.get("/similar-products")
def similar_products(
    product_id: str,
    category_id: str = "",
    page: int = 1,
    size: int = 8
):
    data = fallback_search(product_id, category_id, page, size)
    return {"results": format_response(data)}