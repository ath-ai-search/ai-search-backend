from fastapi import APIRouter, Query
from app.models.search import SearchRequest, AIAssistantRequest, AIAssistantResponse
from app.services.search_service import execute_search, execute_autocomplete, process_ai_assistant

router = APIRouter()

@router.post("")
async def search_products(request: SearchRequest):
    """
    1. Standard Grid Search and Filtering Endpoint.
    This route handles the main product grid searches and UI sidebar filter updates.
    """
    return await execute_search(request)

@router.get("/autocomplete")
async def autocomplete(q: str = Query(..., min_length=1, description="The letters the user is typing")):
    """
    2. Typeahead Datalist Endpoint for the Main Search Bar.
    This provides instant product suggestions as you type.
    """
    return await execute_autocomplete(q)

@router.post("/ai-assistant", response_model=AIAssistantResponse)
async def ai_assistant(request: AIAssistantRequest):
    """
    ✨ 3. DYNAMIC AI ASSISTANT CHAT ENDPOINT ✨
    This specialized route handles requests ONLY from the AI assistant chat panel.
    It passes the user's message AND their current search state to the backend
    service, allowing the 'brain' to make context-aware decisions (filtering vs. switching).
    """
    # This calls the complex AI context-switching function we are building in services.
    return await process_ai_assistant(request.chat_message, request.current_state)