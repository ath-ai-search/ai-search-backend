from fastapi import FastAPI, Query 
from fastapi.middleware.cors import CORSMiddleware
from app.routers import search  
from app.services.search_service import execute_autocomplete, get_mega_menu_widget

app = FastAPI(title="ATH AI Search API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      
    allow_credentials=True,
    allow_methods=["*"],      
    allow_headers=["*"],      
)

app.include_router(search.router, prefix="/search", tags=["Search"])

@app.get("/")
async def root():
    return {"message": "Search API is Online"}

@app.get("/autocomplete")
async def autocomplete(q: str = Query(..., min_length=1)):
    return await execute_autocomplete(q)

@app.get("/widget/autocomplete")
async def mega_menu_endpoint(
    q: str = Query("", description="The search query"),
    recent: str = Query("", description="List of recent searches separated by ||")
):
    return await get_mega_menu_widget(q, recent)