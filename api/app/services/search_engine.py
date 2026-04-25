"""
=====================================================================================
👑 MAIN SEARCH ENGINE (LOCKED IN)
=====================================================================================
STRICT MODE: Pure Facets, True Global Counts, Perfect Sorting.
=====================================================================================
"""

import json
import hashlib
import logging
import time
import re

from app.config import os_client, INDEX_NAME, openai_client
from app.models.search import SearchRequest
from app.utils.brand_mapper import get_smart_brand
from app.utils.pagination import build_pagination_html
from app.utils.cache import cache_get, cache_set
from app.nlp.semantic_matrix import extract_semantic_matrix

from app.core.constants import (
    MAX_OS_WINDOW, DEFAULT_PAGE_SIZE, SMALL_PAGE_SIZE,
    BOOST_NAME_PHRASE, BOOST_BRAND_PHRASE, BOOST_CATEGORY_MATCH,
    BOOST_CROSS_FIELDS, BOOST_FUZZY_FALLBACK, ACCESSORY_DEMOTION_WEIGHT,
    KNN_MIN_K, KNN_BUFFER, SEARCH_CACHE_TTL, CACHE_VERSION,
    FACET_CATEGORIES_SIZE, FACET_BRANDS_SIZE, FACET_COLORS_SIZE,      
    FACET_SIZES_SIZE, FACET_STORAGE_SIZE, FACET_RAM_SIZE,         
    MAX_CATEGORY_FILTERS, MAX_COLOR_FILTERS, MAX_SIZE_FILTERS,
    MAX_BRAND_FILTERS, MAX_GENDER_FILTERS, AI_EMBEDDING_MODEL,
    DEMO_RATING_BASE, DEMO_RATING_RANGE, DEMO_SALES_BASE,
    DEMO_SALES_RANGE, SCORE_DISPLAY_MIN, SCORE_DISPLAY_RANGE,
)
logger = logging.getLogger(__name__)

MIN_RELEVANCE_SCORE = 25.0  # 🆕 Stricter threshold — removes weak vector matches
async def execute_search(request: SearchRequest) -> dict:
    _start_time = time.perf_counter()  # 🆕 Start timing    
    request.page_size = DEFAULT_PAGE_SIZE if request.page_size != SMALL_PAGE_SIZE else SMALL_PAGE_SIZE
    
    request_data = request.model_dump()
    request_str = json.dumps(request_data, sort_keys=True)
    cache_key = f"search:ai:{CACHE_VERSION}:{hashlib.md5(request_str.encode()).hexdigest()}"
    
    cached_result = await cache_get(cache_key)
    if cached_result: return cached_result
    
    max_safe_page = MAX_OS_WINDOW // request.page_size
    
    if request.page > max_safe_page:
        return {"total_results": 0, "total_pages": max_safe_page, "current_page": request.page, "pagination_html": build_pagination_html(max_safe_page, request.page), "results": [], "facets": {"categories": []}}
    
    from_val = (request.page - 1) * request.page_size
    
    query_text = request.query.strip() if request.query else ""
    matrix = extract_semantic_matrix(query_text)
    core_query = matrix["core_query"]
    
    if "|" in core_query:
        multi_items = [item.strip() for item in core_query.split("|") if item.strip()]
        core_query_for_vector = " ".join(multi_items)
    else:
        multi_items = [core_query]
        core_query_for_vector = core_query
    
    vector = None
    if core_query_for_vector:
        try:
            resp = await openai_client.embeddings.create(input=core_query_for_vector, model=AI_EMBEDDING_MODEL)
            vector = resp.data[0].embedding
        except Exception as e:
            logger.error(f"❌ OpenAI Embedding Failed: {e}")
    
    filters = [{"term": {"in_stock": True}}]
    must_nots = []
    
    if matrix["min_price"] is not None or matrix["max_price"] is not None:
        price_range = {}
        if matrix["min_price"] is not None: price_range["gte"] = matrix["min_price"]
        if matrix["max_price"] is not None: price_range["lte"] = matrix["max_price"]
        filters.append({"range": {"price": price_range}})
    
    if (matrix["is_sale"] or request.sort == "on_sale" or (request.filters and getattr(request.filters, "on_sale", False))):
        filters.append({"range": {"sale_price": {"gt": 0}}})
    
    if request.filters:
        if getattr(request.filters, "category", None): filters.append({"terms": {"category": request.filters.category[:MAX_CATEGORY_FILTERS]}})
        if getattr(request.filters, "in_stock", None) is not None: filters.append({"term": {"in_stock": request.filters.in_stock}})
        if getattr(request.filters, "color", None):
            color_shoulds = [{"multi_match": {"query": c, "type": "phrase", "fields": ["color", "colors", "name"]}} for c in request.filters.color[:MAX_COLOR_FILTERS]]
            filters.append({"bool": {"should": color_shoulds, "minimum_should_match": 1}})
        if getattr(request.filters, "size", None):
            size_shoulds = [{"multi_match": {"query": str(s).strip() if "size" in str(s).lower() else f"size {str(s).strip()} {str(s).strip()}", "fields": ["size", "sizes", "name"], "type": "best_fields"}} for s in request.filters.size[:MAX_SIZE_FILTERS]]
            filters.append({"bool": {"should": size_shoulds, "minimum_should_match": 1}})
        if getattr(request.filters, "gender", None):
            gender_shoulds = [{"multi_match": {"query": str(g).strip(), "fields": ["gender", "attributes.gender", "category", "name"], "type": "best_fields"}} for g in request.filters.gender[:MAX_GENDER_FILTERS]]
            filters.append({"bool": {"should": gender_shoulds, "minimum_should_match": 1}})
        if getattr(request.filters, "brand", None):
            brand_shoulds = []
            for b in request.filters.brand[:MAX_BRAND_FILTERS]:
                b_str = str(b).strip()
                brand_shoulds.extend([{"match_phrase": {"brand": b_str}}, {"term": {"brand": b_str}}, {"term": {"brand": b_str.upper()}}, {"term": {"brand": b_str.title()}}])
            filters.append({"bool": {"should": brand_shoulds, "minimum_should_match": 1}})
        if getattr(request.filters, "price", None):
            p_range = {}
            if getattr(request.filters.price, "min", None) is not None:
                try: p_range["gte"] = float(re.sub(r'[^\d.]', '', str(request.filters.price.min)))
                except: pass
            if getattr(request.filters.price, "max", None) is not None:
                try: p_range["lte"] = float(re.sub(r'[^\d.]', '', str(request.filters.price.max)))
                except: pass
            if p_range: filters.append({"range": {"price": p_range}})
        if getattr(request.filters, "storage", None):
            storage_values = [str(s).strip() for s in request.filters.storage[:10] if str(s).strip()]
            if storage_values: filters.append({"terms": {"storage": storage_values}})
        if getattr(request.filters, "ram", None):
            ram_values = [str(r).strip() for r in request.filters.ram[:10] if str(r).strip()]
            if ram_values: filters.append({"terms": {"ram": ram_values}})
    
    sort_query = [{"_score": "desc"}]
    if request.sort == "price_asc": sort_query = [{"price": "asc"}]
    elif request.sort == "price_desc": sort_query = [{"price": "desc"}]
    elif request.sort == "on_sale": sort_query = [{"_score": "desc"}]
    
    semantic_shoulds = []
    if vector:
        k_val = min(max(KNN_MIN_K, from_val + request.page_size + KNN_BUFFER), MAX_OS_WINDOW, 300)  
        semantic_shoulds.append({"knn": {"embedding": {"vector": vector, "k": k_val, "boost": 0.3}}})    
    for item in multi_items:
        semantic_shoulds.extend([
            {"match_phrase": {"name": {"query": item, "boost": BOOST_NAME_PHRASE}}},
            {"match_phrase": {"brand": {"query": item, "boost": BOOST_BRAND_PHRASE}}},
            {"match": {"category": {"query": item, "boost": BOOST_CATEGORY_MATCH}}},
            {"multi_match": {"query": item, "fields": ["name^10", "brand^5", "category^3", "description"], "type": "cross_fields", "operator": "and", "boost": BOOST_CROSS_FIELDS}},
            {"multi_match": {"query": item, "fields": ["name^5", "brand^3", "category^2", "description"], "type": "best_fields", "fuzziness": "AUTO", "boost": BOOST_FUZZY_FALLBACK}}
        ])
    
    score_functions = []
    if not matrix["has_accessory_intent"]:
        for acc in matrix["accessory_keywords"]:
            score_functions.append({"filter": {"match": {"name": acc}}, "weight": ACCESSORY_DEMOTION_WEIGHT})
            score_functions.append({"filter": {"match": {"category": acc}}, "weight": ACCESSORY_DEMOTION_WEIGHT})
    
    # 🆕 STRICT ENTERPRISE MATCH (Live Fix)
    # 1. REMOVED "description" to stop garbage products from matching!
    # 2. Uses "cross_fields" so "Adidas" matches the Brand and "Shoes" matches the Category perfectly.
    # 🆕 BALANCED MATCHING (Fixes 0 results for descriptive words)
    must_clauses = []
    if core_query:
        for item in multi_items:
            must_clauses.append({
                "multi_match": {
                    "query": item,
                    "fields": ["name^7", "category^4", "brand^3"], 
                    "type": "cross_fields",
                    "operator": "or",
                    "minimum_should_match": "50%"
                }
            })
    
    if vector or core_query:
        bool_query = {"should": semantic_shoulds, "must_not": must_nots, "minimum_should_match": 1, "filter": filters}
        if must_clauses:
            bool_query["must"] = must_clauses
        query_body = {"query": {"function_score": {"query": {"bool": bool_query}, "functions": score_functions, "score_mode": "multiply", "boost_mode": "multiply"}}}
    else:
        query_body = {"query": {"bool": {"must": [{"match_all": {}}], "filter": filters, "must_not": must_nots}}}
    
    use_min_score = bool(vector or core_query)
    min_relevance_score = MIN_RELEVANCE_SCORE if use_min_score else 0.0
    actual_total_hits = 0
    
    if use_min_score:
        count_query_body = {**query_body, "track_total_hits": True, "min_score": min_relevance_score, "size": 0}
        try:
            count_response = os_client.search(index=INDEX_NAME, body=count_query_body)
            actual_total_hits = count_response.get("hits", {}).get("total", {}).get("value", 0)
        except Exception:
            actual_total_hits = 0
            
    if use_min_score and actual_total_hits > 0:
        real_total_pages = (actual_total_hits + request.page_size - 1) // request.page_size
        if request.page > min(real_total_pages, max_safe_page):
            return {"total_results": actual_total_hits, "total_pages": min(real_total_pages, max_safe_page), "current_page": request.page, "pagination_html": build_pagination_html(min(real_total_pages, max_safe_page), request.page), "results": [], "facets": {"categories": []}}
    
    # =====================================================================
    # 🚀 OPENSEARCH QUERY: SAMPLER + GLOBAL COUNTS
    # =====================================================================
    os_query = {
        "from": from_val,
        "size": request.page_size,
        **query_body,
        "sort": sort_query,
        "track_total_hits": True,
        "track_scores": True,
        "min_score": min_relevance_score,
        
        "aggs": {
            # 1. STRICT SAMPLER: Size 100 completely blocks Kitchen, Amazon, Jeans
            "strict_relevance_sampler": {
                "sampler": { "shard_size": 100 },
                "aggs": {
                    "categories": {"terms": {"field": "category", "size": FACET_CATEGORIES_SIZE, "min_doc_count": 3}},
                    "brands": {"terms": {"field": "brand", "size": FACET_BRANDS_SIZE, "min_doc_count": 3}},
                    "colors": {"terms": {"field": "colors", "size": FACET_COLORS_SIZE, "min_doc_count": 2}},
                    "sizes": {"terms": {"field": "sizes", "size": FACET_SIZES_SIZE, "min_doc_count": 2}},
                    "storage": {"terms": {"field": "storage", "size": FACET_STORAGE_SIZE, "min_doc_count": 2}},
                    "ram": {"terms": {"field": "ram", "size": FACET_RAM_SIZE, "min_doc_count": 2}}
                }
            },
            # 2. GLOBAL COUNTS: Generates the true total numbers for the UI
            "global_categories": {"terms": {"field": "category", "size": FACET_CATEGORIES_SIZE}},
            "global_brands": {"terms": {"field": "brand", "size": FACET_BRANDS_SIZE}},
            "global_colors": {"terms": {"field": "colors", "size": FACET_COLORS_SIZE}},
            "global_sizes": {"terms": {"field": "sizes", "size": FACET_SIZES_SIZE}},
            "global_storage": {"terms": {"field": "storage", "size": FACET_STORAGE_SIZE}},
            "global_ram": {"terms": {"field": "ram", "size": FACET_RAM_SIZE}}
        }
    }
    
    try: response = os_client.search(index=INDEX_NAME, body=os_query)
    except Exception as e: return {"error": "Search service unavailable", "results": [], "total_results": 0, "total_pages": 0, "current_page": request.page, "pagination_html": "", "facets": {"categories": []}}
    
    hits = response.get("hits", {})
    total_hits = actual_total_hits if (use_min_score and actual_total_hits > 0) else hits.get("total", {}).get("value", 0)
    
    raw_total_pages = (total_hits + request.page_size - 1) // request.page_size if total_hits > 0 else 0
    total_pages = min(raw_total_pages, max_safe_page)
    max_score = hits.get("max_score") or 1.0
    
    results = []
    for hit in hits.get("hits", []):
        source = hit.get("_source", {})
        brand_display = get_smart_brand(source)
        
        raw_cats = source.get("category", [])
        clean_cats = [c.strip() for c in re.sub(r"[\[\]'\"]", "", raw_cats).split(",") if c.strip()] if isinstance(raw_cats, str) else [str(c).strip() for c in raw_cats if c and str(c).strip()]
        if not clean_cats or clean_cats == ["None"]: clean_cats = ["Uncategorized"]
        
        images = source.get("images", [])
        primary_image = images[0] if isinstance(images, list) and len(images) > 0 else None
        
        _pid = str(source.get("product_id", "123"))
        _pid_hash = int(hashlib.md5(_pid.encode()).hexdigest(), 16)
        
        raw_score = hit.get("_score", 0) or 0
        normalized_score = min(1.0, raw_score / max_score) if max_score > 0 else 0
        
        results.append({
            "id": source.get("product_id"),
            "name": source.get("name", "Unknown Product"),
            "description": source.get("description", ""),
            "brand": brand_display,
            "category": clean_cats,
            "price": source.get("price", 0.0),
            "sale_price": source.get("sale_price"),
            "in_stock": source.get("in_stock", False),
            "sku": source.get("sku", ""),
            "url": source.get("url", ""),
            "primary_image": primary_image,
            "rating": source.get("rating") if source.get("rating", 0) > 0 else DEMO_RATING_BASE + (_pid_hash % DEMO_RATING_RANGE) / 10.0,
            "sales_count": source.get("sales_count") if source.get("sales_count", 0) > 0 else (_pid_hash % DEMO_SALES_RANGE) + DEMO_SALES_BASE,
            "score": round(SCORE_DISPLAY_MIN + (normalized_score * SCORE_DISPLAY_RANGE), 2)
        })
    
    if request.sort not in ["price_asc", "price_desc"]: results.sort(key=lambda x: x["score"], reverse=True)
    
    # =====================================================================
    # 🚀 STEP 16: PARSER - PERFECT SORTING
    # =====================================================================
    sampled_aggs = response.get("aggregations", {}).get("strict_relevance_sampler", {})
    all_aggs = response.get("aggregations", {})
    
    def build_smart_facet_list(agg_name: str, global_agg_name: str) -> list:
        # Step A: Get pure names from the top 100
        sampled_buckets = sampled_aggs.get(agg_name, {}).get("buckets", [])
        allowed_keys = set()
        for bucket in sampled_buckets:
            val = str(bucket.get("key", "")).strip()
            if val and val.lower() not in ["none", "default", "default title", "uncategorized", ""]:
                allowed_keys.add(val)
        
        if not allowed_keys: return []

        # Step B: Get the massive global counts for those pure names
        global_buckets = all_aggs.get(global_agg_name, {}).get("buckets", [])
        global_counts = {}
        for bucket in global_buckets:
            val = str(bucket.get("key", "")).strip()
            global_counts[val] = bucket.get("doc_count", 0)
            
        result = []
        for val in allowed_keys:
            result.append({
                "value": val,
                "label": val,
                "count": global_counts.get(val, 0) # Real math
            })
            
        # Step C: Perfect UX Sorting (Highest Global Number to Lowest)
        result.sort(key=lambda x: x["count"], reverse=True)
        return result

    facets = {}
    cat_list = build_smart_facet_list("categories", "global_categories")
    if cat_list: facets["categories"] = cat_list
    brand_list = build_smart_facet_list("brands", "global_brands")
    if brand_list: facets["brands"] = brand_list
    color_list = build_smart_facet_list("colors", "global_colors")
    if color_list: facets["colors"] = color_list
    size_list = build_smart_facet_list("sizes", "global_sizes")
    if size_list: facets["sizes"] = size_list
    storage_list = build_smart_facet_list("storage", "global_storage")
    if storage_list: facets["storage"] = storage_list
    ram_list = build_smart_facet_list("ram", "global_ram")
    if ram_list: facets["ram"] = ram_list

    final_response = {
        "total_results": total_hits,
        "total_pages": total_pages,
        "current_page": request.page,
        "pagination_html": build_pagination_html(total_pages, request.page),
        "results": results,
        "facets": facets
    }
    
    await cache_set(cache_key, final_response, ttl_seconds=SEARCH_CACHE_TTL)
    
    # 🆕 LOG TIMING
    _elapsed_ms = (time.perf_counter() - _start_time) * 1000
    print(f"⏱️  SEARCH | query='{request.query}' | page={request.page} | total={total_hits} | time={_elapsed_ms:.2f}ms", flush=True)
    
    return final_response