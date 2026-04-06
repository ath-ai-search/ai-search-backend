from fastapi import FastAPI
from app.routers import search

app = FastAPI(title="ATH AI Search API")

# Connect the search router
app.include_router(search.router, prefix="/search", tags=["Search"])