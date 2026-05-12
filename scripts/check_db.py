import os
import boto3
import psycopg2
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
from dotenv import load_dotenv

# ==========================================
# 1. LOAD CREDENTIALS
# ==========================================
load_dotenv()

# OpenSearch Credentials
host = os.getenv("OPENSEARCH_HOST", "").replace("https://", "").replace("/", "")
region = os.getenv("OPENSEARCH_REGION", "us-west-2")
index_name = os.getenv("OPENSEARCH_INDEX", "products")

# PostgreSQL Credentials
DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "port":     os.getenv("DB_PORT", "5432"),
    "database": os.getenv("DB_NAME", "venue_ai"),
    "user":     os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "shubham16"),
}

# ==========================================
# 2. CONNECT TO OPENSEARCH
# ==========================================
credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, 'aoss', session_token=credentials.token)
client = OpenSearch(
    hosts=[{'host': host, 'port': 443}],
    http_auth=awsauth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection
)

print("\n" + "="*60)
print("🔥 PART 1: TOP TRENDING PRODUCTS (From OpenSearch)")
print("="*60)

# Query OpenSearch for the top 5 products sorted by trending_score
response = client.search(
    index=index_name,
    body={
        "size": 5,
        "_source": [
            "product_id", "name", "trending_score", 
            "stats_views", "stats_clicks", "stats_carts", 
            "stats_wishlist", "stats_purchases"
        ],
        "sort": [{"trending_score": "desc"}]
    }
)

# Print the exact data stored in OpenSearch
hits = response.get("hits", {}).get("hits", [])
if not hits:
    print("⚠️ No products found in OpenSearch!")
else:
    for item in hits:
        data = item["_source"]
        print(f"📦 Product ID : {data.get('product_id')}")
        print(f"🏷️  Name       : {data.get('name')}")
        print(f"🔥 Trend Score: {data.get('trending_score')}")
        print(f"👁️  Views      : {data.get('stats_views', 0)}")
        print(f"🖱️  Clicks     : {data.get('stats_clicks', 0)}")
        print(f"🛒  Carts      : {data.get('stats_carts', 0)}")
        print(f"⭐  Wishlist   : {data.get('stats_wishlist', 0)}")
        print(f"💳  Purchases  : {data.get('stats_purchases', 0)}")
        print("-" * 40)


print("\n" + "="*60)
print("🕒 PART 2: MOST RECENT ACTIVITY (Timeline from PostgreSQL)")
print("="*60)

try:
    # Connect to PostgreSQL
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # Fetch the 5 most recently touched products
    cursor.execute("""
        SELECT product_id, views, clicks, carts, wishlist, purchases, last_seen 
        FROM product_metrics 
        ORDER BY last_seen DESC 
        LIMIT 5;
    """)
    
    recent_rows = cursor.fetchall()
    
    if not recent_rows:
        print("⚠️ No recent activity found in PostgreSQL.")
    else:
        # Step 1: Extract all the recent product IDs
        recent_pids = [str(row[0]) for row in recent_rows]
        
        # Step 2: Ask OpenSearch for the NAMES of these specific products
        name_map = {}
        if recent_pids:
            os_res = client.search(
                index=index_name,
                body={
                    "size": len(recent_pids),
                    "_source": ["product_id", "name"],
                    "query": {"terms": {"product_id": recent_pids}}
                }
            )
            for h in os_res.get("hits", {}).get("hits", []):
                src = h.get("_source", {})
                name_map[str(src.get("product_id"))] = src.get("name", "Unknown Product Name")

        # Step 3: Print the Recent Timeline with Names included!
        for row in recent_rows:
            product_id, views, clicks, carts, wishlist, purchases, last_seen = row
            prod_name = name_map.get(str(product_id), "Unknown Product Name")
            
            print(f"📦 Product ID : {product_id}")
            print(f"🏷️  Name       : {prod_name}")
            print(f"🕒 Last Seen  : {last_seen.strftime('%Y-%m-%d %H:%M:%S')} (UTC)")
            print(f"📊 Stats      : 👁️ Views: {views} | 🖱️ Clicks: {clicks} | 🛒 Carts: {carts} | ⭐ Wish: {wishlist} | 💳 Purch: {purchases}")
            print("-" * 40)
            
except Exception as e:
    print(f"❌ Database error: {e}")
finally:
    if 'cursor' in locals(): cursor.close()
    if 'conn' in locals(): conn.close()


# ==========================================
# 4. VERIFY TRENDING API'S SALE-ONLY FILTER
# ==========================================
print("\n" + "="*60)
print("🛍️  PART 3: TOP 5 SALE PRODUCTS (Trending API Filter Test)")
print("="*60)
print("Replicates the exact filter used by /trending API:")
print("  - trending_score > 1")
print("  - sale_price > 0 (must be on sale)")
print("  - Sorted by trending_score DESC")
print("-" * 60)

response_sale = client.search(
    index=index_name,
    body={
        "size": 5,
        "_source": [
            "product_id", "name", "trending_score",
            "price", "sale_price", "in_stock"
        ],
        "query": {
            "bool": {
                "must": [
                    {"range": {"trending_score": {"gt": 1}}},
                    {"range": {"sale_price": {"gt": 0}}}
                ]
            }
        },
        "sort": [{"trending_score": "desc"}]
    }
)

hits_sale = response_sale.get("hits", {}).get("hits", [])

if not hits_sale:
    print("⚠️ No sale products found! Sale filter may not be working correctly.")
else:
    print(f"✅ Found {len(hits_sale)} sale products. Showing top 5:\n")
    
    for idx, item in enumerate(hits_sale, 1):
        data = item["_source"]
        
        try:
            price = float(data.get("price", 0) or 0)
        except (TypeError, ValueError):
            price = 0.0
        try:
            sale_price = float(data.get("sale_price", 0) or 0)
        except (TypeError, ValueError):
            sale_price = 0.0
        
        # Calculate discount %
        discount_pct = 0.0
        if price > 0 and 0 < sale_price < price:
            discount_pct = ((price - sale_price) / price) * 100
        
        # Sanity check flag
        if discount_pct >= 1.0:
            flag = "✅ VALID SALE"
        elif sale_price > 0 and sale_price >= price:
            flag = "⚠️ FAKE SALE (sale_price >= price)"
        else:
            flag = "❓ EDGE CASE"
        
        print(f"  #{idx} {flag}")
        print(f"     📦 Product ID  : {data.get('product_id')}")
        print(f"     🏷️  Name        : {data.get('name', '')[:60]}")
        print(f"     🔥 Trend Score : {data.get('trending_score')}")
        print(f"     💰 Price       : ${price:.2f}")
        print(f"     🏷️  Sale Price  : ${sale_price:.2f}")
        print(f"     🎯 Discount    : {discount_pct:.1f}% OFF")
        print(f"     📦 In Stock    : {data.get('in_stock', True)}")
        print("-" * 60)
    
    # Summary
    valid_sales = sum(
        1 for item in hits_sale
        if (float(item["_source"].get("price", 0) or 0) > 0
            and 0 < float(item["_source"].get("sale_price", 0) or 0) < float(item["_source"].get("price", 0) or 0))
    )
    print(f"\n📊 SUMMARY: {valid_sales}/{len(hits_sale)} have valid discounts (sale_price < price)")
    
    if valid_sales == len(hits_sale):
        print("✅ Trending API sale filter is working PERFECTLY!")
    else:
        print(f"⚠️ {len(hits_sale) - valid_sales} products have sale_price >= price (fake sales). May need cleanup.")