import os
import requests
from dotenv import load_dotenv

# Load variables from your .env file
load_dotenv()

# Pulling strictly from your .env file
OPENSEARCH_URL = os.getenv("OPENSEARCH_HOST")
INDEX = os.getenv("OPENSEARCH_INDEX", "products")

# ✅ ADD THESE TWO LINES TO CHECK:
print(f"DEBUG: OPENSEARCH_URL is: {OPENSEARCH_URL}")
print(f"DEBUG: INDEX is: {INDEX}")