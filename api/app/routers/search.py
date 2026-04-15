from fastapi import APIRouter, Query
from pydantic import BaseModel
from app.models.search import SearchRequest
from app.services.search_service import execute_search, execute_autocomplete, process_ai_assistant

router = APIRouter()

# =========================================================================
# 📥 NEW: AI ASSISTANT PAYLOAD MODEL
# =========================================================================
class AIAssistantRequest(BaseModel):
    """
    Captures the user's new chat message AND their current search state.
    This allows the AI to know if "blue" means "blue shoes" (filtering) 
    or if "show me dresses" means abandoning the shoes entirely (new search).
    """
    chat_message: str
    current_state: SearchRequest


# =========================================================================
# 🌐 ENDPOINTS
# =========================================================================

@router.post("")
async def search_products(request: SearchRequest):
    """Standard grid search and filtering endpoint."""
    return await execute_search(request)


@router.get("/autocomplete")
async def autocomplete(q: str = Query(..., min_length=1, description="The letters the user is typing")):
    """Typeahead dropdown endpoint for the main search bar."""
    return await execute_autocomplete(q)


@router.post("/ai-assistant")
async def ai_assistant(request: AIAssistantRequest):
    """
    🟢 NEW: Dedicated endpoint for the AI Assistant Chat.
    Passes the chat message and the current search parameters to the LLM 
    to decide whether to filter the current grid or start a brand new search.
    """
    return await process_ai_assistant(
        chat_message=request.chat_message, 
        current_state=request.current_state
    )