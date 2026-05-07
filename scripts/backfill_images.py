"""
ONE-TIME backfill — fixes 'images' order in OpenSearch using sort_order.
Only touches products with trending activity. ~5 min total.
"""
import os, asyncio, logging, boto3, httpx
from dotenv import load_dotenv
from opensearchpy import OpenSearch, RequestsHttpConnection, helpers
from requests_aws4auth import AWS4Auth

logging.basicConfig(level="INFO", format="%(asctime)s  %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("BackfillImages")
load_dotenv()

STORE = os.getenv("BIGCOMMERCE_STORE_HASH")
TOKEN = os.getenv("BIGCOMMERCE_ACCESS_TOKEN")
OS_HOST = os.getenv("OPENSEARCH_HOST", "").replace("https://", "").replace("/", "")
OS_REGION = os.getenv("OPENSEARCH_REGION", "us-west-2")
OS_INDEX = os.getenv("OPENSEARCH_INDEX", "products")

def get_os_client():
    creds = boto3.Session().get_credentials()
    auth = AWS4Auth(creds.access_key, creds.secret_key, OS_REGION, 'aoss', session_token=creds.token)
    return OpenSearch(hosts=[{'host': OS_HOST, 'port': 443}], http_auth=auth,
                      use_ssl=True, verify_certs=True, connection_class=RequestsHttpConnection, timeout=60)

async def fetch_images(pid, http):
    url = f"https://api.bigcommerce.com/stores/{STORE}/v3/catalog/products/{pid}/images"
    try:
        r = await http.get(url, headers={"X-Auth-Token": TOKEN, "Accept": "application/json"})
        if r.status_code != 200: return []
        data = r.json().get("data", [])
        # Sort: is_thumbnail first, then sort_order ascending
        data.sort(key=lambda x: (0 if x.get("is_thumbnail") else 1, x.get("sort_order", 9999)))
        return [img.get("url_standard") or img.get("url_thumbnail", "") for img in data[:5] if img.get("url_standard") or img.get("url_thumbnail")]
    except Exception as e:
        logger.error(f"❌ {pid}: {e}")
        return []

async def main():
    client = get_os_client()
    res = client.search(index=OS_INDEX, body={
        "size": 10000, "_source": ["product_id"],
        "query": {"range": {"trending_score": {"gt": 1}}}
    })
    targets = [(h["_id"], h["_source"]["product_id"]) for h in res["hits"]["hits"]]
    logger.info(f"📊 Found {len(targets)} products")

    actions = []
    async with httpx.AsyncClient(timeout=30.0) as http:
        for i, (os_id, pid) in enumerate(targets):
            imgs = await fetch_images(pid, http)
            if imgs:
                actions.append({
                    "_op_type": "update", "_index": OS_INDEX, "_id": os_id,
                    "doc": {"images": imgs}, "doc_as_upsert": False
                })
            if (i+1) % 50 == 0:
                logger.info(f"   {i+1}/{len(targets)} processed")
            await asyncio.sleep(0.1)  # rate limit safety

    if actions:
        ok, _ = helpers.bulk(client, actions, raise_on_error=False, chunk_size=100)
        logger.info(f"✅ Updated images for {ok} products")
    else:
        logger.info("⚠️  No actions to apply")

if __name__ == "__main__":
    asyncio.run(main())