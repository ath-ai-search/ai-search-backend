import os
import boto3
import redis.asyncio as redis
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
from dotenv import load_dotenv

# ✅ FIX 1: Match the path where Terraform saves the .env file
load_dotenv("/opt/pipeline/api/.env")

# --- OpenSearch Setup ---
def get_opensearch_client():
    region = os.getenv("OPENSEARCH_REGION", "us-west-2")
    credentials = boto3.Session().get_credentials()
    auth = AWSV4SignerAuth(credentials, region, 'aoss')

    raw_host = os.getenv("OPENSEARCH_HOST", "")
    clean_host = raw_host.replace("https://", "").replace("/", "")

    client = OpenSearch(
        hosts=[{'host': clean_host, 'port': 443}],
        http_auth=auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection
    )
    return client

os_client = get_opensearch_client()
INDEX_NAME = os.getenv("OPENSEARCH_INDEX", "products")

# --- Redis Setup ---
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# ✅ FIX 2: Added timeouts to prevent the API from hanging if Redis is busy
redis_client = redis.from_url(
    REDIS_URL, 
    decode_responses=True, 
    encoding="utf-8",
    socket_connect_timeout=5,  # Time to establish connection
    socket_timeout=5          # Time to wait for a response
)