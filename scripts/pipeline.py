"""
scripts/pipeline.py
================
MANUAL pipeline — run once to bulk sync all products
from BigCommerce into OpenSearch.

    pip install httpx python-dotenv opensearch-py boto3 requests openai
    python scripts/pipeline.py

=====================================================================================
🆕 ADDED IN THIS VERSION: Dynamic Variant Extraction
=====================================================================================
This pipeline now extracts product variants (sizes, colors, storage, etc.)
from BigCommerce and stores them in OpenSearch for dynamic faceted filtering.

What's NEW (compared to previous version):
  ✅ Extracts variant data from raw["variants"] (was being ignored before)
  ✅ Detects option types dynamically (Size, Color, Storage, RAM, etc)
  ✅ Stores them as searchable fields in OpenSearch
  ✅ New field: has_variants (true/false) — tells frontend if variants exist
  ✅ New field: variant_options — list of option types (e.g., ["Size", "Color"])
  ✅ New field: sizes, colors, storage, ram, etc — dynamic arrays

What's UNCHANGED:
  ✅ All existing logic (fetching, transforming, embedding, indexing)
  ✅ AI embedding generation (same OpenAI model and code)
  ✅ Rate limit handling
  ✅ Pagination
  ✅ Error handling
  ✅ Main run() function
=====================================================================================
"""

import asyncio
import logging
import re
from typing import AsyncGenerator
import os
from dotenv import load_dotenv
import httpx
import boto3
import psycopg2

logging.basicConfig(
    level="INFO",
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Load the .env file from the current directory
load_dotenv()

CONFIG = {
    "BIGCOMMERCE_STORE_HASH":   os.getenv("BIGCOMMERCE_STORE_HASH"),
    "BIGCOMMERCE_ACCESS_TOKEN": os.getenv("BIGCOMMERCE_ACCESS_TOKEN"),
    "OPENAI_API_KEY":           os.getenv("OPENAI_API_KEY", ""), 
    "OPENSEARCH_HOST":          os.getenv("OPENSEARCH_HOST"),
    "OPENSEARCH_REGION":        os.getenv("OPENSEARCH_REGION", "us-west-2"),
    "OPENSEARCH_INDEX":         os.getenv("OPENSEARCH_INDEX", "products"),
    "DELETE_EXISTING_INDEX":    True, 
}

def get_postgres_metrics() -> dict:
    logger.info("📊 Fetching historical metrics from PostgreSQL...")
    metrics_map = {}
    try:
        conn = psycopg2.connect(host="localhost", database="venue_ai", user="postgres", password="shubham16")
        cursor = conn.cursor()
        cursor.execute("SELECT product_id, views, clicks, carts, purchases, wishlist FROM product_metrics;")
        for row in cursor.fetchall():
            product_id, views, clicks, carts, purchases, wishlist = row
            trending_score = 1.0 + (views * 1) + (clicks * 2) + (wishlist * 3) + (carts * 5) + (purchases * 10)
            metrics_map[str(product_id)] = {
                "trending_score": trending_score, "stats_views": views, "stats_clicks": clicks, "stats_carts": carts, "stats_purchases": purchases
            }
    except Exception as e:
        logger.error(f"❌ Could not connect to Postgres: {e}")
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()
    return metrics_map

# ============================================================
# BIGCOMMERCE EXTRACTOR
# ============================================================

class BigCommerceExtractor:
    def __init__(self, store_hash: str, access_token: str):
        self.base_url = f"https://api.bigcommerce.com/stores/{store_hash}/v3"
        self.headers  = {
            "X-Auth-Token": access_token,
            "Content-Type": "application/json",
            "Accept":       "application/json",
        }

    async def get_category_map(self) -> dict:
        logger.info("📥 Fetching Category Tree from BigCommerce...")
        cat_map = {}
        page = 1
        async with httpx.AsyncClient(timeout=30.0) as client:
            while True:
                resp = await client.get(
                    f"{self.base_url}/catalog/categories",
                    params={"page": page, "limit": 250},
                    headers=self.headers
                )
                resp.raise_for_status()
                data = resp.json()
                
                for cat in data.get("data", []):
                    cat_map[cat["id"]] = cat["name"]
                
                total_pages = data.get("meta", {}).get("pagination", {}).get("total_pages", 1)
                if page >= total_pages:
                    break
                page += 1
                await asyncio.sleep(0.2)
        logger.info(f"✅ Memorized {len(cat_map)} Categories.")
        return cat_map

    async def get_brand_map(self) -> dict:
        logger.info("📥 Fetching Brand Dictionary from BigCommerce...")
        brand_map = {}
        page = 1
        async with httpx.AsyncClient(timeout=30.0) as client:
            while True:
                resp = await client.get(
                    f"{self.base_url}/catalog/brands",
                    params={"page": page, "limit": 250},
                    headers=self.headers
                )
                resp.raise_for_status()
                data = resp.json()
                
                for brand in data.get("data", []):
                    brand_map[brand["id"]] = brand["name"]
                
                total_pages = data.get("meta", {}).get("pagination", {}).get("total_pages", 1)
                if page >= total_pages:
                    break
                page += 1
                await asyncio.sleep(0.2)
        logger.info(f"✅ Memorized {len(brand_map)} Brands.")
        return brand_map

    async def get_all_products(
        self,
        start_page: int = 1,
        end_page:   int = 9999,
    ) -> AsyncGenerator[list[dict], None]:
        page = start_page
        async with httpx.AsyncClient(timeout=30.0) as client:
            while page <= end_page:
                logger.info(f"Fetching page {page}...")

                for attempt in range(3):
                    try:
                        resp = await client.get(
                            f"{self.base_url}/catalog/products",
                            params={
                                "page":         page,
                                "limit":        100,
                                "include":      "variants,images,custom_fields",
                                "availability": "available",
                                "is_visible":   "true",
                            },
                            headers=self.headers,
                        )
                        if resp.status_code == 429:
                            wait = int(resp.headers.get("X-Rate-Limit-Time-Reset-Ms", 1500)) / 1000
                            logger.warning(f"Rate limited — waiting {wait:.1f}s...")
                            await asyncio.sleep(wait)
                            continue
                        resp.raise_for_status()
                        break
                    except Exception as e:
                        logger.error(f"Attempt {attempt + 1} failed: {e}")
                        if attempt == 2:
                            raise
                        await asyncio.sleep(2 ** attempt)

                data     = resp.json()
                products = data.get("data", [])
                if not products:
                    logger.info("No more products.")
                    break

                logger.info(f"Page {page}: {len(products)} products received")
                yield products

                total_pages = data.get("meta", {}).get("pagination", {}).get("total_pages", 1)
                if page >= total_pages or page >= end_page:
                    break

                page += 1
                await asyncio.sleep(1.0)

    async def get_product_count(self) -> int:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{self.base_url}/catalog/products",
                params={"limit": 1, "availability": "available", "is_visible": "true"},
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json().get("meta", {}).get("pagination", {}).get("total", 0)


# ============================================================
# PRODUCT TRANSFORMER
# ============================================================

def strip_html(html_string: str) -> str:
    if not html_string:
        return ""
    clean = __import__("re").sub(r"<[^>]+>", " ", html_string)
    for old, new in [("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
                     ("&quot;", '"'), ("&#39;", "'"), ("&nbsp;", " ")]:
        clean = clean.replace(old, new)
    return __import__("re").sub(r"\s+", " ", clean).strip()

def is_product_eligible(raw: dict) -> bool:
    if not raw.get("is_visible", True):
        return False
    if raw.get("availability", "") != "available":
        return False
    if float(raw.get("price", 0) or 0) <= 0:
        return False
    if (raw.get("inventory_level", 0) or 0) <= 0:
        return False
    return True


# ============================================================
# 🆕 NEW HELPER: VARIANT EXTRACTOR (DYNAMIC)
# ============================================================
# This function extracts variant options dynamically from BigCommerce data.
# Works for ANY product type — shoes, phones, laptops, etc.
# Automatically detects what options exist (Size, Color, Storage, RAM, etc)
# and organizes them into clean arrays for OpenSearch.
#
# Example input (BigCommerce variant data):
#   [
#     {
#       "id": 789,
#       "sku": "NIKE-001-BLK-9",
#       "price": 99.99,
#       "option_values": [
#         {"option_display_name": "Size", "label": "9"},
#         {"option_display_name": "Color", "label": "Black"}
#       ]
#     },
#     ...
#   ]
#
# Example output:
#   {
#     "has_variants": True,
#     "variant_options": ["Size", "Color"],
#     "variants_count": 15,
#     "sizes": ["7", "8", "9", "10"],
#     "colors": ["Black", "White", "Red"]
#   }
# ============================================================

def extract_variant_data(raw_variants: list) -> dict:
    """
    Extracts variant options dynamically from BigCommerce variants array.
    
    ARGS:
        raw_variants: List of variant dicts from BigCommerce API
    
    RETURNS:
        dict with variant info — ready to merge into product data
    
    STRATEGY:
        1. Loop through all variants
        2. Read each variant's option_values
        3. Group values by option name (Size, Color, Storage, etc)
        4. SKIP "Default" option (BigCommerce adds this to ALL products)
        5. Only mark as has_variants=True if REAL variants exist
        6. Return as clean arrays for OpenSearch
    """
    
    # Start with empty result — no variants detected yet
    variant_data = {
        "has_variants": False,
        "variant_options": [],
        "variants_count": 0,
    }
    
    # Safety check: if variants is None or empty, return empty result
    if not raw_variants or not isinstance(raw_variants, list):
        return variant_data
    
    # Dictionary to collect values by option name
    # Example: {"Size": {"7", "8", "9"}, "Color": {"Black", "White"}}
    options_collected = {}
    
    # Loop through each variant
    for variant in raw_variants:
        # Safety: skip if variant is not a dictionary
        if not isinstance(variant, dict):
            continue
        
        # Get this variant's option_values (the actual size/color/etc)
        option_values = variant.get("option_values", [])
        
        if not option_values or not isinstance(option_values, list):
            continue
        
        # Loop through each option value
        for opt in option_values:
            if not isinstance(opt, dict):
                continue
            
            # Get the option name (like "Size", "Color", "Storage")
            option_name = str(opt.get("option_display_name", "")).strip()
            
            # Get the actual value (like "9", "Black", "128GB")
            option_value = str(opt.get("label", "")).strip()
            
            # Skip if either is empty
            if not option_name or not option_value:
                continue
            
            # 🆕 SKIP "Default" options — BigCommerce creates these automatically
            # for ALL products (even simple ones). These are NOT real variants.
            if option_name.lower() in ["default", "default title", "title"]:
                continue
            
            # 🆕 Also skip if the VALUE is "Default Title" (common BigCommerce default)
            if option_value.lower() in ["default title", "default"]:
                continue
            
            # Add to our collection
            if option_name not in options_collected:
                options_collected[option_name] = set()
            
            options_collected[option_name].add(option_value)
    
    # If we didn't find any REAL options, this is a simple product (no variants)
    if not options_collected:
        return variant_data
    
    # 🆕 EXTRA CHECK: If we only have 1 variant AND it doesn't have meaningful options,
    # treat it as simple product (not a real variant product)
    # Real variant products typically have 2+ variants
    if len(raw_variants) <= 1:
        # Only 1 variant = not really a variant product
        return variant_data
    
    # ✅ We have REAL variant data! Build the final result
    variant_data["has_variants"] = True
    variant_data["variants_count"] = len(raw_variants)
    variant_data["variant_options"] = sorted(options_collected.keys())
    
    # Convert each option to a lowercase field name + sorted list
    for option_name, values_set in options_collected.items():
        # Convert option name to safe field name
        field_name = option_name.lower().replace(" ", "_").replace("-", "_")
        
        # Pluralize common options
        if field_name in ["size", "color"]:
            field_name = field_name + "s"
        
        # Store sorted list of values
        variant_data[field_name] = sorted(list(values_set))
    
    return variant_data


def transform_product(raw: dict, category_map: dict, brand_map: dict, metrics_map: dict) -> dict:
    try:
        product_id  = str(raw.get("id", ""))
        name        = raw.get("name", "").strip()
        description = strip_html(raw.get("description", ""))
        
        brand_id = raw.get("brand_id")
        brand = brand_map.get(brand_id, "") if brand_id else ""
        if not brand:
            brand = raw.get("brand_name", "") or ""

        categories = []
        for cat in raw.get("categories", []):
            if isinstance(cat, dict):
                categories.append(cat.get("name", ""))
            elif isinstance(cat, (int, str)):
                cat_id_int = int(cat) if str(cat).isdigit() else cat
                cat_name = category_map.get(cat_id_int)
                if cat_name:
                    categories.append(cat_name)
                else:
                    categories.append(str(cat))

        price      = float(raw.get("price", 0) or 0.0)
        sale_price = raw.get("sale_price")
        sale_price = float(sale_price) if sale_price and float(sale_price) > 0 else 0.0

        inventory = raw.get("inventory_level", 0) or 0
        in_stock  = raw.get("availability") == "available" or inventory > 0

        images = []
        for img in raw.get("images", [])[:5]:
            if isinstance(img, dict):
                url = img.get("url_standard") or img.get("url_thumbnail", "")
                if url:
                    images.append(url)

        attributes = {}
        for cf in raw.get("custom_fields", []):
            if isinstance(cf, dict):
                k = str(cf.get("name", "")).strip()
                v = str(cf.get("value", "")).strip()
                if k and v:
                    attributes[k] = v

        url        = ""
        custom_url = raw.get("custom_url", {})
        if isinstance(custom_url, dict):
            url = custom_url.get("url", "")

        # =================================================================
        # 🆕 NEW: EXTRACT VARIANT DATA (sizes, colors, storage, etc)
        # =================================================================
        # Uses the new extract_variant_data() helper function
        # Returns a dict like: {"has_variants": True, "sizes": [...], "colors": [...]}
        # For products WITHOUT variants: returns {"has_variants": False}
        # This runs AFTER all other data extraction, so it doesn't break anything
        variant_data = extract_variant_data(raw.get("variants", []))
        # =================================================================

        search_parts = [name]
        if brand:
            search_parts.append(brand)
        search_parts.extend(categories)
        if description:
            search_parts.append(description[:500])
        for k, v in list(attributes.items())[:10]:
            search_parts.append(f"{k}: {v}")
        
        # =================================================================
        # 🆕 NEW: Add variant info to search_text too (helps AI embeddings)
        # =================================================================
        # Example: search_text gets "Size: 7 | Size: 8 | Color: Black | Color: Red"
        # This makes AI embeddings aware of variant options
        if variant_data.get("has_variants"):
            for opt_name in variant_data.get("variant_options", []):
                # Get the field name (like "sizes", "colors")
                field_name = opt_name.lower().replace(" ", "_").replace("-", "_")
                if field_name in ["size", "color"]:
                    field_name = field_name + "s"
                
                values = variant_data.get(field_name, [])
                if values:
                    # Add first 5 values to search_text (limit for speed)
                    search_parts.append(f"{opt_name}: {', '.join(values[:5])}")
        # =================================================================

        # ✅ FIXED: Prevent crashing by safely handling missing/empty data
        result = {
            "product_id":      product_id,
            "name":            name,
            "description":     description,
            "brand":           brand,
            "category":        categories,
            "price":           price,
            "sale_price":      sale_price,
            "in_stock":        in_stock,
            "sku":             raw.get("sku", "") or "",
            "images":          images,
            "attributes":      attributes,
            "url":             url,
            "weight":          float(raw.get("weight", 0) or 0.0),
            "inventory_level": inventory,
            "search_text":     " | ".join(search_parts),
            "sort_order":      int(raw.get("sort_order", 0) or 0),
            "total_sold":      int(raw.get("total_sold", 0) or 0)
        }
        
        # =================================================================
        # 🆕 NEW: Merge variant data into result
        # =================================================================
        # This adds all variant fields (has_variants, sizes, colors, etc)
        # to the final product data that gets indexed in OpenSearch
        result.update(variant_data)
        # =================================================================
        # 🧠 SMART MATCHER: Handles both Numeric IDs and URL Slugs!
        
        # 1. Clean up the BigCommerce URL to get just the text slug
        # Example: "/dinggu-steel-toe-shoes/" becomes "dinggu-steel-toe-shoes"
        slug = url.strip("/").split("/")[-1] if url else ""
        
        # 2. Try ID first. If it fails, try Slug. If BOTH fail, default to 0.
        product_stats = metrics_map.get(product_id) or metrics_map.get(slug) or {
            "trending_score": 1.0, 
            "stats_views": 0, 
            "stats_clicks": 0, 
            "stats_carts": 0, 
            "stats_purchases": 0
        }
        
        result.update(product_stats)
        # =================================================================
        date_mod = raw.get("date_modified", "")
        if date_mod:
            result["date_modified"] = date_mod

        return result

    except Exception as e:
        logger.error(f"Transform failed for product {raw.get('id')}: {e}")
        return {
            "product_id":  str(raw.get("id", "")),
            "name":        raw.get("name", ""),
            "search_text": raw.get("name", ""),
        }

def transform_batch(raw_products: list[dict], category_map: dict, brand_map: dict, metrics_map: dict) -> list[dict]:
    results, skipped = [], 0
    for raw in raw_products:
        if not is_product_eligible(raw):
            skipped += 1
            continue
        transformed = transform_product(raw, category_map, brand_map, metrics_map)
        if transformed.get("product_id"):
            results.append(transformed)
    if skipped:
        logger.info(f"Filtered: {len(results)} eligible, {skipped} skipped")
    return results


# ============================================================
# EMBEDDING GENERATOR
# ============================================================

async def generate_embeddings(products: list[dict], api_key: str) -> list[dict]:
    if not api_key:
        logger.warning("No OPENAI_API_KEY — filling with dummy zero embeddings (1536 dims)")
        for p in products:
            p["embedding"] = [0.0] * 1536
        return products

    try:
        import openai
        client = openai.AsyncOpenAI(api_key=api_key)

        texts = []
        for p in products:
            parts = [p.get("name", "")]
            if p.get("brand"):
                parts.append(p["brand"])
            parts.extend(p.get("category", []))
            if p.get("description"):
                parts.append(p["description"][:500])
            for k, v in list(p.get("attributes", {}).items())[:5]:
                parts.append(f"{k}: {v}")
            texts.append(" | ".join(parts))

        all_embeddings = []
        for i in range(0, len(texts), 100):
            batch = texts[i:i + 100]
            resp  = await client.embeddings.create(
                model="text-embedding-3-small",
                input=batch,
            )
            all_embeddings.extend([item.embedding for item in resp.data])
            logger.info(f"Embeddings: {len(all_embeddings)}/{len(texts)}")
            if i + 100 < len(texts):
                await asyncio.sleep(0.5)

        for idx, p in enumerate(products):
            p["embedding"] = all_embeddings[idx] if idx < len(all_embeddings) else [0.0] * 1536

    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        for p in products:
            if "embedding" not in p:
                p["embedding"] = [0.0] * 1536

    return products


# ============================================================
# OPENSEARCH INDEXER
# ============================================================

# ✅ FIXED: Simplified for AWS Vector Serverless compatibility 
# 🆕 ADDED: Variant fields (has_variants, sizes, colors, storage, ram, etc)
PRODUCT_MAPPING = {
    "settings": {
        "index.knn": True,
    },
    "mappings": {
        "properties": {
            "product_id":    {"type": "keyword"},
            "name":          {"type": "text"},
            "description":   {"type": "text"},
            "brand":         {"type": "keyword"},
            "category":      {"type": "keyword"},
            "price":         {"type": "float"},
            "sale_price":    {"type": "float"},
            "in_stock":      {"type": "boolean"},
            "sku":           {"type": "keyword"},
            "url":           {"type": "keyword"},
            "attributes":    {"type": "object", "dynamic": True},
            "search_text":   {"type": "text"},
            "sort_order":    {"type": "integer"},
            "total_sold":    {"type": "integer"},
            "date_modified": {"type": "date", "ignore_malformed": True},
            "trending_score":  {"type": "float"},
            "stats_views":     {"type": "integer"},
            "stats_clicks":    {"type": "integer"},
            "stats_carts":     {"type": "integer"},
            "stats_purchases": {"type": "integer"},
            # =================================================================
            # 🆕 NEW VARIANT FIELDS (for dynamic faceted filtering)
            # =================================================================
            # These fields are automatically populated by extract_variant_data()
            # Products WITHOUT variants will simply not have these fields
            # Products WITH variants will have them populated dynamically
            
            "has_variants":    {"type": "boolean"},
            "variant_options": {"type": "keyword"},  # ["Size", "Color"]
            "variants_count":  {"type": "integer"},
            
            # Common variant fields (stored as keyword arrays for filtering)
            "sizes":   {"type": "keyword"},
            "colors":  {"type": "keyword"},
            "storage": {"type": "keyword"},
            "ram":     {"type": "keyword"},
            # Note: Any OTHER dynamic option field (like "material", "style")
            # will automatically be added as keyword type by OpenSearch
            # because "dynamic" is allowed in the mapping
            # =================================================================
            
            "embedding": {
                "type":      "knn_vector",
                "dimension": 1536,
                "method":    {"name": "hnsw", "space_type": "l2", "engine": "nmslib"},
            },
        }
    },
}

class OpenSearchIndexer:
    def __init__(self, host: str, region: str, index_name: str = "products"):
        from opensearchpy import OpenSearch, helpers, RequestsHttpConnection, AWSV4SignerAuth
        import boto3
        
        self.helpers    = helpers
        self.index_name = index_name
        
        clean_host = host.replace("https://", "").rstrip("/")
        credentials = boto3.Session().get_credentials()
        auth = AWSV4SignerAuth(credentials, region, 'aoss')

        self.client     = OpenSearch(
            hosts=[{'host': clean_host, 'port': 443}],
            http_auth=auth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
            pool_maxsize=20,
            timeout=60,
        )

    def create_index(self, delete_existing: bool = False):
        exists = self.client.indices.exists(index=self.index_name)
        if exists:
            if delete_existing:
                self.client.indices.delete(index=self.index_name)
                logger.info(f"Deleted existing index: {self.index_name}")
            else:
                logger.info(f"Index '{self.index_name}' exists — upserting docs")
                return
        self.client.indices.create(index=self.index_name, body=PRODUCT_MAPPING)
        logger.info(f"Created index: {self.index_name}")

    def bulk_index(self, products: list[dict]) -> dict:
        if not products:
            return {"indexed": 0, "errors": 0}
        actions = [
            {"_index": self.index_name, "_source": p}
            for p in products if p.get("product_id")
        ]
        
        success, errors = self.helpers.bulk(
            self.client, actions,
            raise_on_error=False,
            raise_on_exception=False,
            chunk_size=50,
            request_timeout=60,
        )
        
        error_count = len(errors) if isinstance(errors, list) else 0
        logger.info(f"Bulk index: {success} ok, {error_count} errors")
        
        # ✅ NEW: Emergency Error Printer! If it fails, this reveals exactly why.
        if error_count > 0 and isinstance(errors, list):
            logger.error(f"❌ EXACT REJECTION REASON: {errors[0]}")
            
        return {"indexed": success, "errors": error_count}


# ============================================================
# MAIN
# ============================================================

async def run():
    extractor = BigCommerceExtractor(
        store_hash=CONFIG["BIGCOMMERCE_STORE_HASH"],
        access_token=CONFIG["BIGCOMMERCE_ACCESS_TOKEN"],
    )
    indexer = OpenSearchIndexer(
        host=CONFIG["OPENSEARCH_HOST"],
        region=CONFIG["OPENSEARCH_REGION"],
        index_name=CONFIG["OPENSEARCH_INDEX"],
    )

    total = await extractor.get_product_count()
    logger.info(f"Total active+visible products in BigCommerce: {total}")

    category_map = await extractor.get_category_map()
    brand_map = await extractor.get_brand_map()
    
    metrics_map = get_postgres_metrics()

    indexer.create_index(delete_existing=CONFIG["DELETE_EXISTING_INDEX"])

    total_indexed, total_errors = 0, 0

    async for raw_page in extractor.get_all_products():
        products = transform_batch(raw_page, category_map, brand_map, metrics_map)
        if not products:
            continue
        
        products = await generate_embeddings(products, CONFIG["OPENAI_API_KEY"])
        
        result   = indexer.bulk_index(products)
        total_indexed += result["indexed"]
        total_errors  += result["errors"]

    logger.info("=" * 50)
    logger.info(f"Sync complete — indexed: {total_indexed}, errors: {total_errors}")
    logger.info("=" * 50)


if __name__ == "__main__":
    asyncio.run(run())