from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import search  # Adjust this import based on your actual folder structure

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