from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import search

app = FastAPI(title="ATH AI Search API")

# ✅ Allow web browsers to talk to this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows any website to connect
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search.router, prefix="/search", tags=["Search"])