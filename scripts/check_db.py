import os
import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
from dotenv import load_dotenv

# Load credentials
load_dotenv()
host = os.getenv("OPENSEARCH_HOST", "").replace("https://", "").replace("/", "")
region = os.getenv("OPENSEARCH_REGION", "us-west-2")
index_name = os.getenv("OPENSEARCH_INDEX", "products")

# Connect securely to AWS OpenSearch
credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, 'aoss', session_token=credentials.token)
client = OpenSearch(
    hosts=[{'host': host, 'port': 443}],
    http_auth=awsauth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection
)

print("\n🔍 Fetching the top trending products directly from OpenSearch...\n")

# Query OpenSearch for the top 5 products sorted by trending_score
response = client.search(
    index=index_name,
    body={
        "size": 5,
        "_source": ["product_id", "name", "trending_score", "stats_views", "stats_clicks"],
        "sort": [{"trending_score": "desc"}]
    }
)

# Print the exact data stored in the database
hits = response.get("hits", {}).get("hits", [])
if not hits:
    print("⚠️ No products found in OpenSearch!")
else:
    for item in hits:
        data = item["_source"]
        print(f"📦 Product ID : {data.get('product_id')}")
        print(f"🏷️  Name       : {data.get('name')}")
        print(f"🔥 Trend Score: {data.get('trending_score')}")
        print(f"👁️  Views      : {data.get('stats_views')}")
        print(f"🖱️  Clicks     : {data.get('stats_clicks')}")
        print("-" * 40)