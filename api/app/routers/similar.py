from fastapi import APIRouter
from app.services.similar_service import (
    get_embedding, 
    ai_search, 
    fallback_search, 
    format_response
)

router = APIRouter(tags=["Similar Products"])


@router.get("/ai-similar-products")
async def ai_similar_products(
    product_id: str,
    category_id: str = "",
    page: int = 1,
    size: int = 8
):
    try:
        vector = get_embedding(product_id)
        
        if vector:
            data = await ai_search(vector, product_id, category_id, page, size)
            results = format_response(data)
            
            if results:
                return {
                    "results": results,
                    "method": "ai_vector",
                    "count": len(results)
                }
        
        print(f"ℹ️  Falling back to text similarity for product {product_id}")
        fallback_data = await fallback_search(product_id, category_id, page, size)
        results = format_response(fallback_data)
        
        return {
            "results": results,
            "method": "text_similarity",
            "count": len(results)
        }
        
    except Exception as e:
        print(f"❌ Similar products error: {e}")
        return {
            "results": [],
            "error": str(e),
            "count": 0
        }


@router.get("/similar-products")
async def similar_products(
    product_id: str,
    category_id: str = "",
    page: int = 1,
    size: int = 8
):
    try:
        data = await fallback_search(product_id, category_id, page, size)
        results = format_response(data)
        
        return {
            "results": results,
            "method": "text_similarity",
            "count": len(results)
        }
    except Exception as e:
        return {
            "results": [],
            "error": str(e),
            "count": 0
        }