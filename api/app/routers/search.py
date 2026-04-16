from fastapi import APIRouter, Query
from app.models.search import SearchRequest, AIAssistantRequest, AIAssistantResponse, AIWelcomeRequest, AIWelcomeResponse
from app.services.search_service import execute_search, execute_autocomplete, process_ai_assistant, generate_ai_welcome

router = APIRouter()

@router.post("")
async def search_products(request: SearchRequest):
    return await execute_search(request)

@router.get("/autocomplete")
async def autocomplete(q: str = Query(..., min_length=1)):
    return await execute_autocomplete(q)

@router.post("/ai-assistant", response_model=AIAssistantResponse)
async def ai_assistant(request: AIAssistantRequest):
    return await process_ai_assistant(request.chat_message, request.current_state)

# 🚀 NEW: The dedicated endpoint for generating dynamic greetings
@router.post("/ai-welcome", response_model=AIWelcomeResponse)
async def ai_welcome(request: AIWelcomeRequest):
    return await generate_ai_welcome(request.current_query)