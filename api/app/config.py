import os
import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
from dotenv import load_dotenv

load_dotenv("/opt/pipeline/scripts/.env")

def get_opensearch_client():
    region = os.getenv("OPENSEARCH_REGION", "us-west-2")
    credentials = boto3.Session().get_credentials()
    auth = AWSV4SignerAuth(credentials, region, 'aoss')

    # ✅ FIX 1: Strip https:// from the Terraform URL
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