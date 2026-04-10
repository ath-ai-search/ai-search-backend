from fastapi import FastAPI, Query  # ✅ NEW: Imported Query
from fastapi.middleware.cors import CORSMiddleware
from app.routers import search  
from app.services.search_service import execute_autocomplete # ✅ NEW: Imported your autocomplete logic

app = FastAPI(title="ATH AI Search API")

# ==========================================
# ✅ ALLOW ALL ORIGINS (CORS)
# ==========================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # Allows any website to access this API
    allow_credentials=True,
    allow_methods=["*"],      # Allows GET, POST, OPTIONS, etc.
    allow_headers=["*"],      # Allows all headers
)

# Include your search router
app.include_router(search.router, prefix="/search", tags=["Search"])

@app.get("/")
async def root():
    return {"message": "Search API is Online"}

# ==========================================
# 🚀 AUTOCOMPLETE ENDPOINT 
# ==========================================
@app.get("/autocomplete")
async def autocomplete(q: str = Query(..., min_length=1)):
    """Handles the autocomplete dropdown from the frontend"""
    return await execute_autocomplete(q)