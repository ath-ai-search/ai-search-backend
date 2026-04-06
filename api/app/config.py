import os
import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
from dotenv import load_dotenv

# Load your local .env (it will use the server's .env when deployed)
load_dotenv("/opt/pipeline/scripts/.env")

def get_opensearch_client():
    region = os.getenv("OPENSEARCH_REGION", "us-west-2")
    credentials = boto3.Session().get_credentials()
    auth = AWSV4SignerAuth(credentials, region, 'aoss')

    client = OpenSearch(
        hosts=[{'host': os.getenv("OPENSEARCH_HOST"), 'port': 443}],
        http_auth=auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection
    )
    return client

# Create a single instance of the client to share across the app
os_client = get_opensearch_client()
INDEX_NAME = os.getenv("OPENSEARCH_INDEX", "products")