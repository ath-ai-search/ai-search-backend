"""
===============================================================================
scripts/sync_trending.py
===============================================================================
🚀 LIGHTWEIGHT CRON JOB — Auto-sync trending data
Runs every 5 minutes via CRON.
Updates ONLY products with recent activity (fast: 3-10 seconds).
===============================================================================
"""

import os
import logging
import boto3
import psycopg2
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from opensearchpy import OpenSearch, RequestsHttpConnection, helpers
from requests_aws4auth import AWS4Auth

logging.basicConfig(
    level="INFO",
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("SyncTrending")

load_dotenv()

SYNC_WINDOW_MINUTES = 5

DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "port":     os.getenv("DB_PORT", "5432"),
    "database": os.getenv("DB_NAME", "venue_ai"),
    "user":     os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "shubham16"),
}

OPENSEARCH_HOST = os.getenv("OPENSEARCH_HOST")
OPENSEARCH_REGION = os.getenv("OPENSEARCH_REGION", "us-west-2")
OPENSEARCH_INDEX = os.getenv("OPENSEARCH_INDEX", "products")

# 🔥 STRIP https:// and trailing / (same as your config.py does)
if OPENSEARCH_HOST:
    OPENSEARCH_HOST = OPENSEARCH_HOST.replace("https://", "").replace("/", "")

def get_opensearch_client():
    credentials = boto3.Session().get_credentials()
    awsauth = AWS4Auth(
        credentials.access_key,
        credentials.secret_key,
        OPENSEARCH_REGION,
        'aoss',
        session_token=credentials.token
    )
    return OpenSearch(
        hosts=[{'host': OPENSEARCH_HOST, 'port': 443}],
        http_auth=awsauth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        timeout=30
    )


def get_updated_metrics(minutes_ago: int = 5) -> dict:
    """🔥 INCREMENTAL SYNC: Find ONLY products with new or updated activity."""
    logger.info(f"📊 Fetching products updated in last {minutes_ago} minutes...")
    
    metrics_map = {}
    # Find the exact timestamp from 5 minutes ago
    cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # 🔥 SMART FILTER: Only fetch products where `last_seen` is new!
        cursor.execute("""
            WITH recently_updated AS (
                SELECT DISTINCT product_id 
                FROM product_metrics 
                WHERE last_seen >= %s
            )
            SELECT 
                pm.product_id, 
                SUM(pm.views) as total_views, 
                SUM(pm.clicks) as total_clicks, 
                SUM(pm.carts) as total_carts, 
                SUM(pm.purchases) as total_purchases, 
                SUM(pm.wishlist) as total_wishlist
            FROM product_metrics pm
            INNER JOIN recently_updated ru ON pm.product_id = ru.product_id
            GROUP BY pm.product_id;
        """, (cutoff_time,))
        
        for row in cursor.fetchall():
            product_id, views, clicks, carts, purchases, wishlist = row
            
            views = int(views or 0)
            clicks = int(clicks or 0)
            carts = int(carts or 0)
            purchases = int(purchases or 0)
            wishlist = int(wishlist or 0)
            
            trending_score = 1.0 + (views * 1) + (clicks * 2) + (wishlist * 3) + (carts * 5) + (purchases * 10)
            
            metrics_map[str(product_id)] = {
                "trending_score": trending_score,
                "stats_views": views,
                "stats_clicks": clicks,
                "stats_carts": carts,
                "stats_purchases": purchases,
                "stats_wishlist": wishlist
            }
        
        logger.info(f"✅ Found {len(metrics_map)} products with recent activity")
        
    except Exception as e:
        logger.error(f"❌ Database error: {e}")
        return {}
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()
    
    return metrics_map


def update_opensearch(metrics_map: dict) -> int:
    """Bulk update OpenSearch with new trending data."""
    if not metrics_map:
        logger.info("⏭️  No products to update")
        return 0
    
    client = get_opensearch_client()
    
    # 🔥 STEP 1: Find the REAL OpenSearch _id for these products
    product_ids = list(metrics_map.keys())
    
    try:
        res = client.search(
            index=OPENSEARCH_INDEX,
            body={
                "size": len(product_ids),
                "_source": ["product_id"],
                "query": {"terms": {"product_id": product_ids}}
            }
        )
    except Exception as e:
        logger.error(f"❌ Failed to fetch product IDs from OpenSearch: {e}")
        return 0
        
    # Map the readable product_id to the random OpenSearch _id
    real_id_map = {}
    for hit in res.get("hits", {}).get("hits", []):
        os_id = hit["_id"]
        p_id = hit["_source"].get("product_id")
        if p_id:
            real_id_map[str(p_id)] = os_id
            
    # 🔥 STEP 2: Build the update actions using the correct internal ID
    actions = []
    for product_id, data in metrics_map.items():
        os_id = real_id_map.get(str(product_id))
        
        # If the product doesn't exist in OpenSearch, skip it to prevent errors
        if not os_id:
            logger.warning(f"⚠️  Skipping {product_id} - not found in OpenSearch")
            continue
            
        actions.append({
            "_op_type": "update",
            "_index": OPENSEARCH_INDEX,
            "_id": os_id,             # 🔥 Use the REAL OpenSearch _id
            "doc": data,
            "doc_as_upsert": False
        })
    
    success_count = 0
    failed_count = 0
    
    try:
        for ok, item in helpers.streaming_bulk(client, actions, raise_on_error=False, max_retries=2):
            if ok:
                success_count += 1
            else:
                failed_count += 1
                logger.error(f"❌ Update failed reason: {item}") # 🔥 Prints exact API rejection
        
        logger.info(f"✅ Updated {success_count} products in OpenSearch")
        if failed_count > 0:
            logger.warning(f"⚠️  Failed: {failed_count} products")
        
    except Exception as e:
        logger.error(f"❌ OpenSearch error: {e}")
        return 0
    
    return success_count


def main():
    start_time = datetime.now(timezone.utc)
    logger.info("=" * 60)
    logger.info("🚀 SYNC TRENDING — Started (INCREMENTAL MODE)")
    logger.info("=" * 60)
    
    # 🔥 Only grabs new/updated data from the last 5 minutes
    metrics = get_updated_metrics(minutes_ago=SYNC_WINDOW_MINUTES)
    
    if not metrics:
        logger.info("⏭️  Nothing to sync — exiting")
        return
    
    updated = update_opensearch(metrics)
    
    elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
    logger.info("=" * 60)
    logger.info(f"✅ SYNC COMPLETE")
    logger.info(f"   Products: {len(metrics)} processed, {updated} updated")
    logger.info(f"   Time: {elapsed:.2f} seconds")
    logger.info("=" * 60)

if __name__ == "__main__":
 main()