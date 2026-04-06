"""
scripts/sync.py
================
MANUAL pipeline — run once to bulk sync all products
from BigCommerce into OpenSearch.

    pip install httpx openai opensearch-py boto3 requests
    python scripts/pipeline.py
"""

import asyncio
import logging
import re
from typing import AsyncGenerator
import os
from dotenv import load_dotenv
import httpx
import boto3

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
    "OPENSEARCH_REGION":        os.getenv("OPENSEARCH_REGION", "us-west-2"), # Added for Serverless
    "OPENSEARCH_INDEX":         os.getenv("OPENSEARCH_INDEX", "products"),
    "DELETE_EXISTING_INDEX":    False, 
}

# ============================================================


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
    """Only index: available + visible + in-stock + price > 0."""
    if not raw.get("is_visible", True):
        return False
    if raw.get("availability", "") != "available":
        return False
    if float(raw.get("price", 0) or 0) <= 0:
        return False
    if (raw.get("inventory_level", 0) or 0) <= 0:
        return False
    return True


def transform_product(raw: dict) -> dict:
    try:
        product_id  = str(raw.get("id", ""))
        name        = raw.get("name", "").strip()
        description = strip_html(raw.get("description", ""))
        brand       = raw.get("brand_name", "") or ""

        categories = []
        for cat in raw.get("categories", []):
            if isinstance(cat, dict):
                categories.append(cat.get("name", ""))
            elif isinstance(cat, (int, str)):
                categories.append(str(cat))

        price      = float(raw.get("price", 0) or 0)
        sale_price = raw.get("sale_price")
        sale_price = float(sale_price) if sale_price and float(sale_price) > 0 else None

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
                k = cf.get("name", "").strip()
                v = cf.get("value", "").strip()
                if k and v:
                    attributes[k] = v

        url        = ""
        custom_url = raw.get("custom_url", {})
        if isinstance(custom_url, dict):
            url = custom_url.get("url", "")

        search_parts = [name]
        if brand:
            search_parts.append(brand)
        search_parts.extend(categories)
        if description:
            search_parts.append(description[:500])
        for k, v in list(attributes.items())[:10]:
            search_parts.append(f"{k}: {v}")

        return {
            "product_id":      product_id,
            "name":            name,
            "description":     description,
            "brand":           brand,
            "category":        categories,
            "price":           price,
            "sale_price":      sale_price,
            "in_stock":        in_stock,
            "sku":             raw.get("sku", ""),
            "images":          images,
            "attributes":      attributes,
            "url":             url,
            "weight":          float(raw.get("weight", 0) or 0),
            "inventory_level": inventory,
            "search_text":     " | ".join(search_parts),
            "sort_order":      raw.get("sort_order", 0),
            "total_sold":      raw.get("total_sold", 0),
            "date_modified":   raw.get("date_modified", ""),
        }
    except Exception as e:
        logger.error(f"Transform failed for product {raw.get('id')}: {e}")
        return {
            "product_id":  str(raw.get("id", "")),
            "name":        raw.get("name", ""),
            "search_text": raw.get("name", ""),
        }


def transform_batch(raw_products: list[dict]) -> list[dict]:
    results, skipped = [], 0
    for raw in raw_products:
        if not is_product_eligible(raw):
            skipped += 1
            continue
        transformed = transform_product(raw)
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
        logger.warning("No OPENAI_API_KEY — storing zero embeddings")
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

PRODUCT_MAPPING = {
    "settings": {
        "number_of_shards":   5,
        "number_of_replicas": 1,
        # "index.knn":          True,
        "analysis": {
            "analyzer": {
                "autocomplete": {
                    "type":      "custom",
                    "tokenizer": "autocomplete_tokenizer",
                    "filter":    ["lowercase"],
                }
            },
            "tokenizer": {
                "autocomplete_tokenizer": {
                    "type":        "edge_ngram",
                    "min_gram":    2,
                    "max_gram":    15,
                    "token_chars": ["letter", "digit"],
                }
            },
        },
    },
    "mappings": {
        "properties": {
            "product_id":    {"type": "keyword"},
            "name":          {"type": "text", "analyzer": "autocomplete",
                              "fields": {"keyword": {"type": "keyword"}}},
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
            # "embedding": {
            #     "type":      "knn_vector",
            #     "dimension": 1536,
            #     "method":    {"name": "hnsw", "space_type": "l2", "engine": "nmslib"},
            # },
        }
    },
}


class OpenSearchIndexer:
    def __init__(self, host: str, region: str, index_name: str = "products"):
        from opensearchpy import OpenSearch, helpers, RequestsHttpConnection, AWSV4SignerAuth
        import boto3
        
        self.helpers    = helpers
        self.index_name = index_name
        
        # Clean the host URL just in case 'https://' was included in the .env file
        clean_host = host.replace("https://", "").rstrip("/")
        
        # Get IAM credentials securely from the EC2 instance profile
        credentials = boto3.Session().get_credentials()
        
        # Use 'aoss' as the service name for OpenSearch Serverless
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
            {"_index": self.index_name, "_id": p["product_id"], "_source": p}
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

    indexer.create_index(delete_existing=CONFIG["DELETE_EXISTING_INDEX"])

    total_indexed, total_errors = 0, 0

    async for raw_page in extractor.get_all_products():
        products = transform_batch(raw_page)
        if not products:
            continue
        # embeddings removed for serverless search collection
        # products = await generate_embeddings(products, CONFIG["OPENAI_API_KEY"])
        result   = indexer.bulk_index(products)
        total_indexed += result["indexed"]
        total_errors  += result["errors"]

    logger.info("=" * 50)
    logger.info(f"Sync complete — indexed: {total_indexed}, errors: {total_errors}")
    logger.info("=" * 50)


if __name__ == "__main__":
    asyncio.run(run())