import os
import boto3
import redis.asyncio as redis # ✅ Added for Caching
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
from dotenv import load_dotenv

# Load the env file created by your Terraform bootstrap script
load_dotenv("/opt/pipeline/scripts/.env")

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

# --- Redis Setup (New) ---
# This URL is automatically provided by your Secrets Manager via Terraform
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# We use the asyncio version to keep the FastAPI backend non-blocking and fast
redis_client = redis.from_url(
    REDIS_URL, 
    decode_responses=True, 
    encoding="utf-8"
)