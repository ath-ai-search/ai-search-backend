"""
product-processor/handler.py
================================
Triggered by SQS → processes BigCommerce webhook events.
Uses exact same filter + transform logic as sync.py.
Terraform auto-packages this file — no manual zip needed.

Handles:
  - store/product/created           → fetch + filter + transform + index
  - store/product/updated           → fetch + filter + transform + index
                                      (if ineligible → delete from OpenSearch)
  - store/product/deleted           → delete from OpenSearch
  - store/product/inventory/updated → re-check stock → update or delete
"""

import json
import logging
import os
import re

import boto3
import requests
from requests.auth import HTTPBasicAuth

logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))

secrets_client = boto3.client("secretsmanager")
SECRET_NAME    = os.environ["SECRET_NAME"]


# ============================================================
# SECRETS
# ============================================================

def get_secrets() -> dict:
    response = secrets_client.get_secret_value(SecretId=SECRET_NAME)
    return json.loads(response["SecretString"])


# ============================================================
# HELPERS — same logic as sync.py
# ============================================================

def strip_html(html_string: str) -> str:
    if not html_string:
        return ""
    clean = re.sub(r"<[^>]+>", " ", html_string)
    for old, new in [("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
                     ("&quot;", '"'), ("&#39;", "'"), ("&nbsp;", " ")]:
        clean = clean.replace(old, new)
    return re.sub(r"\s+", " ", clean).strip()


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

        # custom fields → attributes
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
            "embedding":       [0.0] * 1536,
        }
    except Exception as e:
        logger.error(f"Transform failed for product {raw.get('id')}: {e}")
        return {}


# ============================================================
# BIGCOMMERCE
# ============================================================

def fetch_product(store_hash: str, access_token: str, product_id: int) -> dict:
    url = (
        f"https://api.bigcommerce.com/stores/{store_hash}"
        f"/v3/catalog/products/{product_id}"
        f"?include=variants,images,custom_fields"
    )
    resp = requests.get(
        url,
        headers={"X-Auth-Token": access_token, "Accept": "application/json"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json().get("data", {})


# ============================================================
# OPENSEARCH
# ============================================================

def index_product(host: str, user: str, password: str, product: dict):
    product_id = product["product_id"]
    resp = requests.put(
        f"{host}/products/_doc/{product_id}",
        auth=HTTPBasicAuth(user, password),
        json=product,
        headers={"Content-Type": "application/json"},
        verify=False,
        timeout=30,
    )
    resp.raise_for_status()
    logger.info(f"Indexed product {product_id} — HTTP {resp.status_code}")


def delete_product(host: str, user: str, password: str, product_id: str):
    resp = requests.delete(
        f"{host}/products/_doc/{product_id}",
        auth=HTTPBasicAuth(user, password),
        verify=False,
        timeout=30,
    )
    if resp.status_code == 404:
        logger.info(f"Product {product_id} not in OpenSearch — skip delete")
        return
    resp.raise_for_status()
    logger.info(f"Deleted product {product_id} from OpenSearch")


# ============================================================
# LAMBDA HANDLER
# ============================================================

def lambda_handler(event, context):
    secrets      = get_secrets()
    store_hash   = secrets["BIGCOMMERCE_STORE_HASH"]
    access_token = secrets["BIGCOMMERCE_ACCESS_TOKEN"]
    os_host      = secrets["OPENSEARCH_HOST"]
    os_user      = secrets["OPENSEARCH_USERNAME"]
    os_pass      = secrets["OPENSEARCH_PASSWORD"]

    for record in event.get("Records", []):
        try:
            body       = json.loads(record["body"])
            product_id = body.get("product_id")
            scope      = body.get("scope", "")

            logger.info(f"Processing product_id={product_id} scope={scope}")

            # ── DELETED ──────────────────────────────────────
            if "deleted" in scope:
                delete_product(os_host, os_user, os_pass, str(product_id))
                continue

            # ── CREATED / UPDATED / INVENTORY UPDATED ────────
            raw = fetch_product(store_hash, access_token, product_id)

            if not raw:
                logger.warning(f"Product {product_id} not found in BigCommerce")
                continue

            if not is_product_eligible(raw):
                logger.info(f"Product {product_id} ineligible — removing from OpenSearch")
                delete_product(os_host, os_user, os_pass, str(product_id))
                continue

            product = transform_product(raw)
            if not product:
                logger.error(f"Transform returned empty for product {product_id}")
                continue

            index_product(os_host, os_user, os_pass, product)

        except Exception as e:
            logger.error(f"Failed to process record: {e}")
            raise e  # re-raise so SQS retries

    return {"status": "processed"}
