"""
ONE-TIME backfill — updates trending fields in OpenSearch for ALL products.
NO re-index. NO BigCommerce. NO embeddings. ~5-15 min total.
Run once, then delete.
"""
import os, logging, boto3, psycopg2
from dotenv import load_dotenv
from opensearchpy import OpenSearch, RequestsHttpConnection, helpers
from requests_aws4auth import AWS4Auth

logging.basicConfig(level="INFO", format="%(asctime)s  %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("Backfill")
load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"), "port": os.getenv("DB_PORT", "5432"),
    "database": os.getenv("DB_NAME", "venue_ai"), "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "shubham16"),
}
OS_HOST = os.getenv("OPENSEARCH_HOST", "").replace("https://", "").replace("/", "")
OS_REGION = os.getenv("OPENSEARCH_REGION", "us-west-2")
OS_INDEX = os.getenv("OPENSEARCH_INDEX", "products")

def get_os_client():
    creds = boto3.Session().get_credentials()
    awsauth = AWS4Auth(creds.access_key, creds.secret_key, OS_REGION, 'aoss', session_token=creds.token)
    return OpenSearch(hosts=[{'host': OS_HOST, 'port': 443}], http_auth=awsauth,
                      use_ssl=True, verify_certs=True, connection_class=RequestsHttpConnection, timeout=60)

def main():
    logger.info("🚀 Backfill started — fetching ALL products with activity from Postgres")
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("""
        SELECT product_id, SUM(views), SUM(clicks), SUM(carts), SUM(purchases), SUM(wishlist)
        FROM product_metrics
        GROUP BY product_id
        HAVING SUM(views + clicks + carts + purchases + wishlist) > 0;
    """)
    rows = cur.fetchall()
    cur.close(); conn.close()
    logger.info(f"📊 Found {len(rows)} products to backfill")

    metrics = {}
    for pid, v, c, ca, p, w in rows:
        v, c, ca, p, w = int(v or 0), int(c or 0), int(ca or 0), int(p or 0), int(w or 0)
        metrics[str(pid)] = {
            "trending_score": 1.0 + v + c*2 + w*3 + ca*5 + p*10,
            "stats_views": v, "stats_clicks": c, "stats_carts": ca,
            "stats_purchases": p, "stats_wishlist": w
        }

    client = get_os_client()
    pids = list(metrics.keys())
    BATCH = 500
    total_updated = 0

    for i in range(0, len(pids), BATCH):
        batch_pids = pids[i:i+BATCH]
        # find real OpenSearch _ids for this batch
        res = client.search(index=OS_INDEX, body={
            "size": len(batch_pids), "_source": ["product_id"],
            "query": {"terms": {"product_id": batch_pids}}
        })
        id_map = {h["_source"]["product_id"]: h["_id"] for h in res.get("hits", {}).get("hits", [])}

        actions = []
        for pid in batch_pids:
            os_id = id_map.get(pid)
            if not os_id: continue
            actions.append({
                "_op_type": "update", "_index": OS_INDEX, "_id": os_id,
                "doc": metrics[pid], "doc_as_upsert": False
            })

        if actions:
            ok, _ = helpers.bulk(client, actions, raise_on_error=False, max_retries=2)
            total_updated += ok
            logger.info(f"✅ Batch {i//BATCH + 1}: updated {ok} / matched {len(actions)}")

    logger.info(f"🎉 DONE — {total_updated} products updated")

if __name__ == "__main__":
    main()