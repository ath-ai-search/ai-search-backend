import os
import psycopg2
from dotenv import load_dotenv

# Load credentials securely from your .env
load_dotenv()

DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "port":     os.getenv("DB_PORT", "5432"),
    "database": os.getenv("DB_NAME", "venue_ai"),
    "user":     os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "shubham16"),
}

print("\n⏳ Fetching the most RECENT activity timeline from PostgreSQL...\n")

try:
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # 🔥 STRICT TIMELINE: Sorting purely by the most recent timestamp
    cursor.execute("""
        SELECT product_id, views, clicks, carts, wishlist, purchases, last_seen 
        FROM product_metrics 
        ORDER BY last_seen DESC 
        LIMIT 5;
    """)
    
    rows = cursor.fetchall()
    if not rows:
        print("⚠️ No recent activity found in the database.")
    else:
        for row in rows:
            product_id, views, clicks, carts, wishlist, purchases, last_seen = row
            print(f"📦 Product ID : {product_id}")
            print(f"🕒 Last Seen  : {last_seen.strftime('%Y-%m-%d %H:%M:%S')} (UTC)")
            print(f"👁️  Views      : {views}")
            print(f"🖱️  Clicks     : {clicks}")
            print(f"🛒  Carts      : {carts}")
            print(f"⭐  Wishlist   : {wishlist}")
            print(f"💳  Purchases  : {purchases}")
            print("-" * 40)
            
except Exception as e:
    print(f"❌ Database error: {e}")
finally:
    if 'cursor' in locals(): cursor.close()
    if 'conn' in locals(): conn.close()