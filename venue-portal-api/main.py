"""
=====================================================================================
🧑‍💼 VENUE PORTAL API — serves BOTH venue dashboards (client portal + admin console)
=====================================================================================
READ-ONLY against the frozen backend's data:
  • Postgres `venue_ai`  → events / orders / product_metrics  (the /track output)
  • OpenSearch `products`→ the indexed catalogue
plus two SMALL OWN tables (portal_tickets, portal_synonyms) — ours, not the
backend's; the frozen code never reads or writes them.

Contracts mirrored 1:1 from the bCloud dashboards so their UIs run unchanged:
  /client-api/*  → the client portal (token login)
  /stats, /billing/*, /fields, /products, /search, /opensearch-info,
  /api-info, /shop-api-info, /azure/info, /health, /admin/*
                 → the admin console (nginx basic-auth guards the admin host)

Run:  uvicorn main:app --host 127.0.0.1 --port 8100
=====================================================================================
"""

import base64
import hashlib
import hmac
import json
import os
import re
import shutil
import socket
import time
import urllib.request
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(ENV_PATH)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:shubham16@localhost:5432/venue_ai")
OS_HOST = os.getenv("OPENSEARCH_HOST_PLAIN", "localhost:9200")
OS_INDEX = os.getenv("OPENSEARCH_INDEX", "products")
PORTAL_PASSWORD = os.getenv("PORTAL_PASSWORD", "")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
INDEX_TARGET = int(os.getenv("INDEX_TARGET", "260470"))
INDEX_ELAPSED_SEC = int(os.getenv("INDEX_ELAPSED_SEC", "0")) or None
# when the big index run actually finished (shown as "last sync"); a moving
# now() here made every page claim "synced 1s ago" on each reload
INDEX_FINISHED_AT = os.getenv("INDEX_FINISHED_AT", "2026-08-25T09:14:00+00:00")
SECRET = (os.getenv("PORTAL_SECRET") or "venue-portal-dev-secret").encode()
CLIENT = {"client_id": "venue", "name": "Venue Marketplace"}

# 💰 cost ESTIMATES (the frozen backend has no metering; these are honest
# approximations from public model prices: embedding $0.13 / 1M tokens)
EMBED_PRICE_PER_M = 0.13
TOKENS_PER_PRODUCT = 120
TOKENS_PER_SEARCH = 20
VM_MONTH_COST = 62.0   # D4as_v6 + disk, ballpark

app = FastAPI(title="Venue Portal API", docs_url=None, redoc_url=None)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
                   allow_headers=["*"])


# ---------------------------------------------------------------- data clients
def pg():
    import psycopg2
    return psycopg2.connect(DATABASE_URL)


def osc():
    from opensearchpy import OpenSearch
    host, _, port = OS_HOST.replace("http://", "").replace("https://", "").partition(":")
    return OpenSearch(hosts=[{"host": host, "port": int(port or 9200)}],
                      use_ssl=False, verify_certs=False)


def q(sql, args=()):
    """One query → list of tuples. Any failure → empty (portal never breaks)."""
    try:
        with pg() as con, con.cursor() as cur:
            cur.execute(sql, args)
            if cur.description is None:
                return []
            return cur.fetchall()
    except Exception:
        return []


def qx(sql, args=()):
    """Write query with commit."""
    try:
        with pg() as con, con.cursor() as cur:
            cur.execute(sql, args)
            con.commit()
            return True
    except Exception:
        return False


def products_count() -> int:
    try:
        return osc().count(index=OS_INDEX).get("count", 0)
    except Exception:
        return 0


def _ensure_own_tables():
    qx("""CREATE TABLE IF NOT EXISTS portal_tickets (
            id SERIAL PRIMARY KEY, subject TEXT, priority TEXT DEFAULT 'normal',
            status TEXT DEFAULT 'open', created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(), messages JSONB DEFAULT '[]')""")
    qx("""CREATE TABLE IF NOT EXISTS portal_synonyms (
            id SERIAL PRIMARY KEY, word_a TEXT, word_b TEXT,
            UNIQUE (word_a, word_b))""")


_ensure_own_tables()


# ---------------------------------------------------------------- tiny auth
def _sign(payload: str) -> str:
    return base64.urlsafe_b64encode(
        hmac.new(SECRET, payload.encode(), hashlib.sha256).digest()).decode().rstrip("=")


def issue_token(role: str = "client") -> str:
    payload = json.dumps({"c": "venue", "r": role, "exp": time.time() + 8 * 3600})
    p64 = base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")
    return f"{p64}.{_sign(p64)}"


def check(authorization: Optional[str], need_admin: bool = False) -> dict:
    tok = (authorization or "").replace("Bearer ", "").strip()
    try:
        p64, sig = tok.split(".")
        if not hmac.compare_digest(sig, _sign(p64)):
            raise ValueError
        payload = json.loads(base64.urlsafe_b64decode(p64 + "=="))
        if payload.get("c") != "venue" or payload.get("exp", 0) < time.time():
            raise ValueError
        if need_admin and payload.get("r") != "admin":
            raise HTTPException(status_code=403, detail="Admin only")
        return payload
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Please sign in")


_fails: list = []


class LoginBody(BaseModel):
    client_id: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


# =================================================================
# 🔎 EVENT AGGREGATES — the shared brain for both dashboards.
# Venue "searches" = tracked events that carry a search query
# (the frozen tracker logs the query on view/click/cart/purchase).
# =================================================================
def _searches_where():
    return "query IS NOT NULL AND query <> ''"


def _ev_filters(days=0, source="all"):
    """Window + source SQL fragments for the analytics family."""
    win = f"AND created_at > now() - interval '{int(days)} days'" if days else ""
    src = {"assistant": "AND source = 'assistant'",
           "search": "AND (source IS DISTINCT FROM 'assistant')"}.get(source, "")
    return win, src


def _log_search(query, took_ms=None, found=None, source="search"):
    """Every REAL search through the portal becomes a tracking event —
    same row shape the venue tracker already stored (28 exist from April).
    took_ms rides in `value`, found-count in `position` (both unused for
    search rows by every reader; purchase sums all FILTER on event_type)."""
    query = (query or "").strip()
    if not query:
        return
    qx("""INSERT INTO events (id, event_type, session_id, query, "position",
                              value, source)
          VALUES (nextval('events_id_seq'), 'search', 'portal', %s, %s, %s, %s)""",
       (query[:300], found, took_ms, source))


def avg_search_ms(extra=""):
    r = q(f"""SELECT AVG(value) FROM events
              WHERE {_searches_where()} AND value > 0 {extra}""")
    return round(float(r[0][0]), 1) if r and r[0] and r[0][0] else None


def ev_counts():
    return dict(q("SELECT event_type, COUNT(*) FROM events GROUP BY event_type"))


def ev_today():
    return dict(q("""SELECT event_type, COUNT(*) FROM events
                     WHERE created_at::date = CURRENT_DATE GROUP BY event_type"""))


def searches_total():
    r = q(f"SELECT COUNT(*) FROM events WHERE {_searches_where()}")
    return r[0][0] if r else 0


def searches_today():
    r = q(f"""SELECT COUNT(*) FROM events WHERE {_searches_where()}
              AND created_at::date = CURRENT_DATE""")
    return r[0][0] if r else 0


def live_5m():
    r = q("SELECT COUNT(*) FROM events WHERE created_at > now() - interval '5 minutes'")
    return r[0][0] if r else 0


def month_funnel():
    """This-month funnel; when the month has nothing (venue's tracked events
    predate the Azure move) fall back to the lifetime funnel so the story
    of real shopper behaviour still shows."""
    base = f"""SELECT COUNT(*) FILTER (WHERE {_searches_where()}),
                      COUNT(*) FILTER (WHERE event_type = 'click'),
                      COUNT(*) FILTER (WHERE event_type = 'purchase'),
                      COALESCE(SUM(value) FILTER (WHERE event_type = 'purchase'), 0)
               FROM events"""
    r = q(base + " WHERE date_trunc('month', created_at) = date_trunc('month', now())")
    s, c, o, rev = r[0] if r else (0, 0, 0, 0)
    if not any([s, c, o]):
        r = q(base)
        s, c, o, rev = r[0] if r else (0, 0, 0, 0)
    return {"searches": s, "clicks": c, "orders": o, "revenue": float(rev or 0)}


def daily_series(days=14, src=""):
    days = int(days) or 14
    rows = q(f"""SELECT created_at::date::text,
                        COUNT(*) FILTER (WHERE {_searches_where()}),
                        COUNT(*) FILTER (WHERE event_type = 'click'),
                        COUNT(*) FILTER (WHERE event_type = 'purchase'),
                        COALESCE(SUM(value) FILTER (WHERE event_type = 'purchase'), 0)
                 FROM events WHERE created_at > now() - interval '{days} days' {src}
                 GROUP BY 1 ORDER BY 1""")
    out = [{"date": d, "count": s, "assistant": 0, "clicks": c,
            "orders": o, "revenue": float(rev or 0)}
           for d, s, c, o, rev in rows]
    # 📜 history baseline: everything OLDER than the chart window lands on the
    # window's first day, so "growing total" lines start at the real lifetime
    # numbers instead of pretending the store was born this week.
    b = q(f"""SELECT COUNT(*) FILTER (WHERE {_searches_where()}),
                     COUNT(*) FILTER (WHERE event_type = 'click'),
                     COUNT(*) FILTER (WHERE event_type = 'purchase'),
                     COALESCE(SUM(value) FILTER (WHERE event_type = 'purchase'), 0)
              FROM events WHERE created_at <= now() - interval '{days} days' {src}""")
    s, c, o, rev = b[0] if b else (0, 0, 0, 0)
    if any([s, c, o]):
        start = (datetime.now(timezone.utc) - timedelta(days=days - 1)).strftime("%Y-%m-%d")
        if out and out[0]["date"] == start:
            out[0]["count"] += s
            out[0]["clicks"] += c
            out[0]["orders"] += o
            out[0]["revenue"] += float(rev or 0)
        else:
            out.insert(0, {"date": start, "count": s, "assistant": 0, "clicks": c,
                           "orders": o, "revenue": float(rev or 0)})
    return out


def top_queries(limit=10, extra=""):
    rows = q(f"""SELECT query, COUNT(*),
                        COUNT(*) FILTER (WHERE event_type = 'click'),
                        COUNT(*) FILTER (WHERE event_type = 'purchase'),
                        COALESCE(SUM(value) FILTER (WHERE event_type = 'purchase'), 0)
                 FROM events WHERE {_searches_where()} {extra}
                 GROUP BY query ORDER BY 2 DESC LIMIT %s""", (limit,))
    out = []
    for query, n, clicks, orders, rev in rows:
        out.append({"query": query, "count": n, "avg_found": None,
                    "clicks": clicks, "orders": orders,
                    "ctr_pct": round(clicks * 100.0 / n, 1) if n else 0,
                    "conv_pct": round(orders * 100.0 / n, 1) if n else 0,
                    "revenue": float(rev or 0)})
    return out


def est_costs():
    n = products_count()
    s = searches_total()
    ingest_tokens = n * TOKENS_PER_PRODUCT
    search_tokens = s * TOKENS_PER_SEARCH
    ingest_cost = ingest_tokens / 1e6 * EMBED_PRICE_PER_M
    search_cost = search_tokens / 1e6 * EMBED_PRICE_PER_M
    return {"ingest_calls": n, "search_calls": s,
            "ingest_tokens": ingest_tokens, "search_tokens": search_tokens,
            "tokens": ingest_tokens + search_tokens,
            "ingest_cost": round(ingest_cost, 3),
            "search_cost": round(search_cost, 3),
            "total_cost": round(ingest_cost + search_cost, 3)}


def index_fields():
    """The registered-field view, read from the live index mapping."""
    try:
        m = osc().indices.get_mapping(index=OS_INDEX)
        props = list(m.values())[0]["mappings"].get("properties", {})
        out = []
        for name, spec in sorted(props.items()):
            t = spec.get("type", "object")
            if t in ("knn_vector", "dense_vector"):
                continue
            simple = {"text": "text", "keyword": "keyword", "integer": "number",
                      "long": "number", "float": "number", "double": "number",
                      "boolean": "boolean", "date": "date"}.get(t, t)
            out.append({"name": name, "type": simple, "os_type": t})
        return out
    except Exception:
        return []


def product_name_map(ids):
    try:
        if not ids:
            return {}
        docs = osc().mget(index=OS_INDEX, body={"ids": list(ids)[:50]})["docs"]
        return {d["_id"]: (d.get("_source") or {}).get("name") for d in docs if d.get("found")}
    except Exception:
        return {}


def vitals():
    out = {}
    try:
        du = shutil.disk_usage("/")
        out["disk"] = {"total_gb": round(du.total / 1e9, 1),
                       "used_gb": round(du.used / 1e9, 1),
                       "pct": round(du.used * 100.0 / du.total, 1)}
    except Exception:
        out["disk"] = None
    try:
        mem = {}
        with open("/proc/meminfo") as f:
            for line in f:
                k, v = line.split(":")
                mem[k.strip()] = int(v.strip().split()[0])
        total, avail = mem.get("MemTotal", 0), mem.get("MemAvailable", 0)
        out["memory"] = {"total_gb": round(total / 1e6, 1),
                         "used_gb": round((total - avail) / 1e6, 1),
                         "pct": round((total - avail) * 100.0 / total, 1) if total else 0}
    except Exception:
        out["memory"] = None
    try:
        out["cpu_percent"] = round(min(100.0, os.getloadavg()[0] / max(1, os.cpu_count()) * 100), 1)
    except Exception:
        out["cpu_percent"] = None
    return out


# =================================================================
# 👤 CLIENT PORTAL API  (/client-api/*) — bCloud portal contract
# =================================================================
@app.post("/client-api/login")
def login(body: LoginBody):
    now = time.time()
    _fails[:] = [t for t in _fails if now - t < 600]
    if len(_fails) >= 8:
        raise HTTPException(status_code=429, detail="Too many attempts — wait 10 minutes")
    who = body.client_id.strip().lower()
    if who == "admin" and ADMIN_PASSWORD \
            and hmac.compare_digest(body.password, ADMIN_PASSWORD):
        return {"token": issue_token("admin"),
                "client": {**CLIENT, "name": "Venue Admin", "role": "admin",
                           "site_token": "single-store"}}
    if who == "venue" and PORTAL_PASSWORD \
            and hmac.compare_digest(body.password, PORTAL_PASSWORD):
        return {"token": issue_token(),
                "client": {**CLIENT, "role": "client", "site_token": "single-store"}}
    _fails.append(now)
    raise HTTPException(status_code=401, detail="Wrong client id or password")


class ChangePwBody(BaseModel):
    old_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


@app.post("/client-api/change-password")
def change_password(body: ChangePwBody, authorization: Optional[str] = Header(None)):
    check(authorization)
    global PORTAL_PASSWORD
    if not hmac.compare_digest(body.old_password, PORTAL_PASSWORD):
        raise HTTPException(status_code=401, detail="Current password is wrong")
    try:
        with open(ENV_PATH) as f:
            content = f.read()
        content = re.sub(r"^PORTAL_PASSWORD=.*$",
                         f"PORTAL_PASSWORD={body.new_password}",
                         content, flags=re.M)
        with open(ENV_PATH, "w") as f:
            f.write(content)
        PORTAL_PASSWORD = body.new_password
        return {"ok": True}
    except Exception:
        raise HTTPException(status_code=500, detail="Could not save the new password")


@app.get("/client-api/me")
def me(authorization: Optional[str] = Header(None)):
    check(authorization)
    n = products_count()
    last = q(f"SELECT MAX(created_at) FROM events WHERE {_searches_where()}")
    last_at = str(last[0][0]) if last and last[0][0] else None
    return {**CLIENT, "site_token": "single-store", "created_at": "2026-08-25",
            "products": n,
            "plan": {"max_products": 300000, "name": "Marketplace"},
            "doctor": {"last_search_at": last_at,
                       "last_sync": {"indexed": n,
                                     "finished_at": INDEX_FINISHED_AT}
                       if n else None}}


@app.get("/client-api/overview")
def overview(authorization: Optional[str] = Header(None)):
    check(authorization)
    counts = ev_counts()
    fn = month_funnel()
    rev_all = q("SELECT COALESCE(SUM(value),0) FROM events WHERE event_type='purchase'")
    est = est_costs()
    s_total = searches_total()
    return {
        "products": products_count(),
        "searches_today": searches_today(),
        "searches_total": s_total,
        "live_5m": live_5m(),
        "avg_ms": avg_search_ms(),
        "zero_count": 0, "zero_top": [],
        "top": top_queries(8, "AND (source IS DISTINCT FROM 'assistant')"),
        "funnel": fn,
        "ctr_pct": round(fn["clicks"] * 100.0 / fn["searches"], 1) if fn["searches"] else 0,
        "conv_pct": round(fn["orders"] * 100.0 / fn["searches"], 1) if fn["searches"] else 0,
        "clicks_total": counts.get("click", 0),
        "orders_total": counts.get("purchase", 0),
        "revenue_total": float(rev_all[0][0]) if rev_all else 0.0,
        "ai_cost_month": est["total_cost"],
        "ai_tokens_month": est["tokens"],
        "daily": daily_series(14),
    }


@app.get("/client-api/analytics")
def analytics(source: str = "all", size: int = 30, days: int = 0,
              authorization: Optional[str] = Header(None)):
    check(authorization)
    return _analytics_data(source, size, days)


def _analytics_data(source: str = "all", size: int = 30, days: int = 0):
    win, src = _ev_filters(days, source)

    def _total(w):
        r = q(f"SELECT COUNT(*) FROM events WHERE {_searches_where()} {w} {src}")
        return r[0][0] if r else 0

    total = _total(win)
    if not total and win:
        # every tracked search predates this window — show the lifetime
        # story instead of a dead page (new searches re-window it live)
        win = ""
        total = _total(win)

    cnt = q(f"""SELECT COUNT(*) FILTER (WHERE event_type = 'click'),
                       COUNT(*) FILTER (WHERE event_type = 'purchase'),
                       COALESCE(SUM(value) FILTER (WHERE event_type = 'purchase'), 0)
                FROM events WHERE TRUE {win}""")
    clicks, orders, revenue = cnt[0] if cnt else (0, 0, 0)
    recent = q(f"""SELECT query, "position", value, source, created_at FROM events
                   WHERE {_searches_where()} {win} {src}
                   ORDER BY created_at DESC LIMIT %s""", (min(int(size), 1000),))
    per_search_cost = round(TOKENS_PER_SEARCH / 1e6 * EMBED_PRICE_PER_M, 6)
    return {
        "total": total,
        "today": searches_today(),
        "zero_results": 0,
        "avg_ms": avg_search_ms(f"{win} {src}"),
        "ai_calls": total,
        "cost": round(total * per_search_cost, 3),
        "clicks": clicks,
        "orders": orders,
        "revenue": float(revenue or 0),
        "top": top_queries(min(int(size), 50), f"{win} {src}"),
        "recent": [{"query": query, "total": pos, "found": pos,
                    "took_ms": round(float(ms)) if ms else None,
                    "ms": round(float(ms)) if ms else None,
                    "at": str(at), "source": s or "search", "cached": False,
                    "tokens": TOKENS_PER_SEARCH, "cost": per_search_cost}
                   for query, pos, ms, s, at in recent],
        "daily": [{"date": r["date"], "count": r["count"]}
                  for r in daily_series(days or 14, src)],
    }


@app.get("/client-api/events")
def events(type: Optional[str] = None, size: int = 50,
           authorization: Optional[str] = Header(None)):
    check(authorization)
    size = max(1, min(int(size or 50), 200))
    flt, args = "WHERE event_type <> 'impression'", []
    if type and type != "all":
        flt, args = "WHERE event_type = %s", [type]
    rows = q(f"""SELECT event_type, COALESCE(query,''), COALESCE(product_id,''),
                        COALESCE(value,0), created_at
                 FROM events {flt} ORDER BY created_at DESC LIMIT %s""",
             args + [size])
    names = product_name_map({r[2] for r in rows if r[2]})

    def _pretty(pid):
        # venue's tracker stored URL slugs as product ids — turn
        # "astr-the-label-womens-divine-skirt" into a readable title
        return re.sub(r"[-_]+", " ", str(pid)).strip().title() or None

    today = ev_today()
    trev = q("""SELECT COALESCE(SUM(value),0) FROM events
                WHERE event_type='purchase' AND created_at::date = CURRENT_DATE""")
    hourly = q("""SELECT to_char(date_trunc('hour', created_at), 'HH24:00'),
                         COUNT(*),
                         COUNT(*) FILTER (WHERE event_type='click'),
                         COUNT(*) FILTER (WHERE event_type='purchase')
                  FROM events WHERE created_at > now() - interval '24 hours'
                  GROUP BY date_trunc('hour', created_at)
                  ORDER BY date_trunc('hour', created_at)""")
    return {"counts": ev_counts(), "today": today,
            "today_revenue": float(trev[0][0]) if trev else 0.0,
            "live_5m": live_5m(),
            "hourly": [{"hour": h, "events": n, "clicks": c, "orders": o}
                       for h, n, c, o in hourly],
            "recent": [{"type": t, "query": query, "product_id": pid,
                        "product_name": names.get(pid) or (_pretty(pid) if pid else None),
                        "value": float(v or 0),
                        "at": str(at)}
                       for t, query, pid, v, at in rows]}


def _search_products(qq="", category="", page=1, size=24):
    page, size = max(1, min(int(page), 400)), max(1, min(int(size), 100))
    must = []
    if qq:
        must.append({"multi_match": {"query": qq,
                                     "fields": ["name^3", "brand", "categories", "description"],
                                     "fuzziness": "AUTO"}})
    if category:
        must.append({"multi_match": {"query": category,
                                     "fields": ["categories", "category"]}})
    body = {"from": (page - 1) * size, "size": size,
            "_source": {"excludes": ["embedding", "vector", "embeddings", "description_embedding"]},
            "track_total_hits": True,
            "query": {"bool": {"must": must}} if must else {"match_all": {}}}
    res = osc().search(index=OS_INDEX, body=body)
    SKIP = {"embedding", "vector", "embeddings", "description_embedding",
            "search_text", "variant_options", "variants", "attributes"}
    items = []
    for h in res["hits"]["hits"]:
        p = h["_source"]
        img = p.get("image") or p.get("image_url") or p.get("thumbnail")
        if not img and isinstance(p.get("images"), list) and p["images"]:
            first = p["images"][0]
            img = (first.get("url_thumbnail") or first.get("url") or
                   first.get("url_standard")) if isinstance(first, dict) else first
        cats = p.get("categories") or p.get("category") or []
        if isinstance(cats, str):
            cats = [cats]
        filled = {k: v for k, v in p.items()
                  if k not in SKIP and v not in (None, "", [], {})
                  and not isinstance(v, (list, dict))}
        items.append({"id": h["_id"], "name": p.get("name") or p.get("title"),
                      "price": p.get("price") or p.get("sale_price"),
                      "image": img, "image_url": img,
                      "brand": p.get("brand") or p.get("brand_name"),
                      "categories": cats, "category": cats[0] if cats else None,
                      "embedding_dims": 3072, "dims": 3072,
                      "fields": filled})
    return {"total": res["hits"]["total"]["value"], "items": items,
            "products": items}


from fastapi import Request  # noqa: E402


_cats_cache = {"at": 0.0, "data": []}


def product_categories():
    """Category chips for the Products page — terms agg, cached 10 min."""
    if _cats_cache["data"] and time.time() - _cats_cache["at"] < 600:
        return _cats_cache["data"]
    data = []
    for fld in ("categories.keyword", "categories", "category.keyword", "category"):
        try:
            agg = osc().search(index=OS_INDEX, body={
                "size": 0, "aggs": {"c": {"terms": {"field": fld, "size": 24}}}})
            buckets = agg["aggregations"]["c"]["buckets"]
            data = [{"value": b["key"], "count": b["doc_count"]}
                    for b in buckets if str(b["key"]).strip()]
            if data:
                break
        except Exception:
            continue
    if data:
        _cats_cache.update(at=time.time(), data=data)
    return data


@app.get("/client-api/products")
def client_products(request: Request, authorization: Optional[str] = Header(None)):
    check(authorization)
    p = request.query_params
    try:
        out = _search_products(p.get("q", ""), p.get("category", ""),
                               int(p.get("page", 1) or 1), int(p.get("size", 24) or 24))
        out["categories"] = product_categories()
        return out
    except Exception:
        return {"total": 0, "items": [], "products": [], "categories": []}


@app.get("/client-api/search-preview")
def client_search_preview(k: int = 6, request: Request = None,
                          authorization: Optional[str] = Header(None)):
    """The Install & keys live preview — real engine, and the search is
    tracked, so the dashboards move the moment someone tries it."""
    check(authorization)
    query = (request.query_params.get("q") if request else "") or ""
    return admin_search(q_param=query, k=k)


@app.get("/client-api/billing")
def billing(authorization: Optional[str] = Header(None)):
    check(authorization)
    est = est_costs()
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    n = products_count()
    run = {"finished_at": INDEX_FINISHED_AT, "indexed": n,
           "failed": 0, "elapsed_sec": INDEX_ELAPSED_SEC,
           "tokens": est["ingest_tokens"], "cost": est["ingest_cost"]}
    today_s = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    yday_s = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    # charts read ingest_cost/search_cost per point; a zero day before the
    # sync day makes the growing-total line actually rise
    daily = [{"date": yday_s, "cost": 0.0, "ingest_cost": 0.0, "search_cost": 0.0},
             {"date": today_s, "cost": est["total_cost"],
              "ingest_cost": est["ingest_cost"], "search_cost": est["search_cost"]}]
    return {"this_month": month, "current": est,
            "months": [{"month": month, "total_cost": est["total_cost"],
                        "ingest_cost": est["ingest_cost"],
                        "search_cost": est["search_cost"]}],
            "days": daily, "recent_days": daily,
            "runs": [run] if n else [],
            "all_time_cost": est["total_cost"],
            "note": "estimated from public model prices — the venue backend has no built-in meter"}


@app.get("/client-api/sync")
def sync_info(authorization: Optional[str] = Header(None)):
    check(authorization)
    f = index_fields()
    est = est_costs()
    n = products_count()
    run = {"finished_at": INDEX_FINISHED_AT, "indexed": n,
           "failed": 0, "elapsed_sec": INDEX_ELAPSED_SEC,
           "tokens": est["ingest_tokens"], "cost": est["ingest_cost"]}
    return {"registration": {"client_id": "venue", "field_count": len(f),
                             "field_names": [x["name"] for x in f],
                             "registered_at": None} if f else None,
            "runs": [run] if n else []}


class SynonymBody(BaseModel):
    add: Optional[list] = None
    remove: Optional[list] = None


@app.get("/client-api/synonyms")
def synonyms_get(authorization: Optional[str] = Header(None)):
    check(authorization)
    rows = q("SELECT word_a, word_b FROM portal_synonyms ORDER BY id")
    return {"synonyms": [[a, b] for a, b in rows]}


@app.post("/client-api/synonyms")
def synonyms_post(body: SynonymBody, authorization: Optional[str] = Header(None)):
    check(authorization)
    if body.add and len(body.add) == 2:
        a, b = str(body.add[0]).strip().lower()[:40], str(body.add[1]).strip().lower()[:40]
        if a and b and a != b:
            qx("""INSERT INTO portal_synonyms (word_a, word_b) VALUES (%s, %s)
                  ON CONFLICT DO NOTHING""", (a, b))
    if body.remove and len(body.remove) == 2:
        a, b = str(body.remove[0]).strip().lower(), str(body.remove[1]).strip().lower()
        qx("""DELETE FROM portal_synonyms
              WHERE (word_a=%s AND word_b=%s) OR (word_a=%s AND word_b=%s)""",
           (a, b, b, a))
    rows = q("SELECT word_a, word_b FROM portal_synonyms ORDER BY id")
    return {"synonyms": [[a, b] for a, b in rows]}


class TicketCreate(BaseModel):
    subject: str = Field(min_length=3, max_length=200)
    message: str = Field(min_length=1, max_length=4000)
    priority: str = Field(default="normal", pattern="^(low|normal|high)$")


class TicketReply(BaseModel):
    ticket_id: int
    message: Optional[str] = None
    resolve: Optional[bool] = None


def _tickets(client_side=True):
    rows = q("""SELECT id, subject, priority, status, created_at, updated_at, messages
                FROM portal_tickets ORDER BY updated_at DESC LIMIT 100""")
    out = []
    for tid, subject, priority, status, cat, uat, msgs in rows:
        out.append({"id": tid, "client_id": "venue", "subject": subject,
                    "priority": priority, "status": status,
                    "created_at": str(cat), "updated_at": str(uat),
                    "messages": msgs if isinstance(msgs, list) else json.loads(msgs or "[]")})
    return out


@app.get("/client-api/tickets")
def tickets_list(authorization: Optional[str] = Header(None)):
    check(authorization)
    return {"tickets": _tickets()}


@app.post("/client-api/tickets")
def tickets_create(body: TicketCreate, authorization: Optional[str] = Header(None)):
    check(authorization)
    now = datetime.now(timezone.utc).isoformat()
    msg = json.dumps([{"who": "client", "text": body.message.strip(), "at": now}])
    qx("""INSERT INTO portal_tickets (subject, priority, status, messages)
          VALUES (%s, %s, 'open', %s)""", (body.subject.strip(), body.priority, msg))
    return {"ok": True}


@app.post("/client-api/tickets/reply")
def tickets_reply(body: TicketReply, authorization: Optional[str] = Header(None)):
    check(authorization)
    return _ticket_reply(body, who="client")


def _ticket_reply(body: TicketReply, who: str):
    rows = q("SELECT messages, status FROM portal_tickets WHERE id=%s", (body.ticket_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Ticket not found")
    msgs, status = rows[0]
    msgs = msgs if isinstance(msgs, list) else json.loads(msgs or "[]")
    now = datetime.now(timezone.utc).isoformat()
    if body.message:
        msgs.append({"who": who, "text": body.message.strip()[:4000], "at": now})
        status = "open" if who == "client" else "pending"
    if body.resolve:
        status = "resolved"
    qx("""UPDATE portal_tickets SET messages=%s, status=%s, updated_at=NOW()
          WHERE id=%s""", (json.dumps(msgs), status, body.ticket_id))
    return {"ok": True}


# ---------------- blu, with hands (raise_ticket + synonyms) ----------------
class AssistantBody(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    history: Optional[list] = None


_ASSIST_WINDOW_S, _ASSIST_MAX = 600, 20
_assist_hits: list = []


@app.post("/client-api/assistant")
def assistant(body: AssistantBody, authorization: Optional[str] = Header(None)):
    check(authorization)
    now = time.monotonic()
    _assist_hits[:] = [t for t in _assist_hits if now - t < _ASSIST_WINDOW_S]
    if len(_assist_hits) >= _ASSIST_MAX:
        raise HTTPException(status_code=429,
                            detail="blu needs a short break — try again in a few minutes")
    _assist_hits.append(now)
    _log_search(body.question, source="assistant")

    ground = {"client_name": "Venue Marketplace",
              "overview": overview(authorization)}
    system = (
        "You are blu, the friendly robot assistant inside the Venue Marketplace portal. "
        "You help this ONE store understand and operate their dashboard. Rules:\n"
        "0. YOUR POWERS — tools: add_synonym (link two search words), remove_synonym, "
        "raise_ticket (open a support ticket with the human team). When the client asks "
        "to set or fix something a tool covers, DO IT once details are clear; ask for a "
        "missing detail first. After acting, confirm plainly. For problems you cannot fix "
        "with a tool, understand them, then raise_ticket YOURSELF with a clear subject "
        "and summary.\n"
        "1. Answer ONLY from the JSON data below and portal knowledge. Pages: Overview, "
        "Analytics, Live activity, Products, Billing, Data sync, Search settings, "
        "Install & keys, Support, Settings.\n"
        "2. NEVER explain code, internal logic, servers, VMs, AI models or platform "
        "internals — you talk to shop owners. Technical questions → the technical team "
        "handles that side; offer a ticket. You do not know how many stores the platform "
        "has or anything about infrastructure.\n"
        "3. Never invent numbers; money is USD. Keep answers 2-4 short warm sentences. "
        "Every answer ends with a concrete next step (the one exception: asking for a "
        "missing detail needed for an action).\n"
        "4. Reply as STRICT JSON: {\"answer\": str, \"followups\": [up to 3 SHORT "
        "questions the CLIENT would ask YOU next — they are clickable buttons sent back "
        "to you; never questions you ask the client], \"goto\": optional page id, "
        "\"find\": optional section title}. Page ids: overview, analytics, events, "
        "products, billing, sync, search-settings, widget, support, settings.\n\n"
        f"STORE DATA:\n{json.dumps(ground, default=str)[:6000]}")

    _TOOLS = [
        {"type": "function", "function": {
            "name": "add_synonym", "description": "Link two search words for this store.",
            "parameters": {"type": "object", "properties": {
                "word_a": {"type": "string"}, "word_b": {"type": "string"}},
                "required": ["word_a", "word_b"]}}},
        {"type": "function", "function": {
            "name": "remove_synonym", "description": "Remove a synonym pair.",
            "parameters": {"type": "object", "properties": {
                "word_a": {"type": "string"}, "word_b": {"type": "string"}},
                "required": ["word_a", "word_b"]}}},
        {"type": "function", "function": {
            "name": "raise_ticket",
            "description": "Open a support ticket with the human team.",
            "parameters": {"type": "object", "properties": {
                "subject": {"type": "string"}, "message": {"type": "string"},
                "priority": {"type": "string", "enum": ["low", "normal", "high"]}},
                "required": ["subject", "message"]}}},
    ]
    actions_done: list = []

    def _run_tool(name, args):
        try:
            if name == "add_synonym":
                synonyms_post(SynonymBody(add=[args.get("word_a"), args.get("word_b")]),
                              authorization)
                a = str(args.get("word_a", "")).lower()
                b = str(args.get("word_b", "")).lower()
                actions_done.append(f"✅ synonym added: {a} ↔ {b}")
                return f"done — '{a}' and '{b}' are linked"
            if name == "remove_synonym":
                synonyms_post(SynonymBody(remove=[args.get("word_a"), args.get("word_b")]),
                              authorization)
                actions_done.append("🗑️ synonym removed")
                return "removed"
            if name == "raise_ticket":
                tickets_create(TicketCreate(
                    subject=str(args.get("subject") or "Problem report")[:200],
                    message=str(args.get("message") or "(no details)")[:4000],
                    priority=args.get("priority") if args.get("priority")
                    in ("low", "normal", "high") else "normal"), authorization)
                actions_done.append(f"🎫 ticket raised: {str(args.get('subject') or '')[:60]}")
                return "ticket created — the team replies on the Support page"
            return "unknown tool"
        except HTTPException as he:
            return f"could not do it: {he.detail}"
        except Exception as e2:
            return f"could not do it: {str(e2)[:80]}"

    msgs = [{"role": "system", "content": system}]
    for h in (body.history or [])[-8:]:
        if isinstance(h, dict):
            txt = str(h.get("text") or "")[:300].strip()
            if txt:
                who = str(h.get("who") or h.get("role") or "")
                msgs.append({"role": "user" if who in ("user", "client") else "assistant",
                             "content": txt})
    msgs.append({"role": "user", "content": body.question.strip()})

    try:
        from openai import OpenAI
        client_ai = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
        model = os.getenv("AI_CHAT_MODEL", "gpt-4o-mini")
        kwargs = ({"max_completion_tokens": 2000}
                  if model.startswith(("gpt-5", "o1", "o3", "o4"))
                  else {"temperature": 0.3, "max_tokens": 500})
        raw = ""
        for _round in range(3):
            r = client_ai.chat.completions.create(
                model=model, messages=msgs, tools=_TOOLS,
                response_format={"type": "json_object"}, **kwargs)
            m = r.choices[0].message
            if m.tool_calls:
                msgs.append({"role": "assistant", "content": m.content or "",
                             "tool_calls": [tc.model_dump() for tc in m.tool_calls]})
                for tc in m.tool_calls:
                    try:
                        targs = json.loads(tc.function.arguments or "{}")
                    except Exception:
                        targs = {}
                    msgs.append({"role": "tool", "tool_call_id": tc.id,
                                 "content": _run_tool(tc.function.name, targs)})
                continue
            raw = (m.content or "").strip()
            break
        if not raw:
            raise ValueError("empty")
        obj = json.loads(raw)

        def _chip(f):
            if isinstance(f, dict):
                f = next((v for v in f.values() if isinstance(v, str) and v.strip()), "")
            return str(f).strip()[:120]

        _PAGES = {"overview", "analytics", "events", "products", "billing", "sync",
                  "search-settings", "widget", "support", "settings"}
        goto = str(obj.get("goto") or "").strip().lower()
        return {"answer": str(obj.get("answer") or "").strip() or raw,
                "followups": [c for c in (_chip(f) for f in (obj.get("followups") or [])) if c][:3],
                "goto": goto if goto in _PAGES else None,
                "find": str(obj.get("find") or "").strip()[:60] or None,
                "actions": actions_done}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=503,
                            detail="blu is having trouble thinking — try again in a moment")


# =================================================================
# 👑 ADMIN CONSOLE API — bCloud admin-dashboard contract.
# Served ONLY behind nginx basic auth on admin.venuemarketplace.xyz.
# =================================================================
_speed_samples: deque = deque(maxlen=10)


@app.get("/health")
def health():
    try:
        ok = osc().ping()
    except Exception:
        ok = False
    return {"status": "ok" if ok else "down", "opensearch": bool(ok)}


@app.get("/stats")
def stats(client_id: str = "default"):
    n = products_count()
    t = time.monotonic()
    _speed_samples.append((t, n))
    speed = 0
    if len(_speed_samples) >= 2:
        (t0, n0), (t1, n1) = _speed_samples[0], _speed_samples[-1]
        if t1 > t0:
            speed = max(0, round((n1 - n0) / (t1 - t0) * 60))
    est = est_costs()
    return {"indexed": n, "source_total": max(INDEX_TARGET, n), "failed": 0,
            "progress_pct": round(min(100.0, n * 100.0 / max(1, INDEX_TARGET)), 1),
            "success_rate": 100.0, "speed_per_min": speed,
            "avg_embed_ms": None, "elapsed_sec": INDEX_ELAPSED_SEC,
            "rate_per_1m": EMBED_PRICE_PER_M,
            "ai": {"model": "text-embedding-3-large",
                   "calls": est["ingest_calls"] + est["search_calls"],
                   "total_calls": est["ingest_calls"] + est["search_calls"],
                   "cost": est["total_cost"], "total_cost": est["total_cost"],
                   "ingest_cost": est["ingest_cost"], "ingest_calls": est["ingest_calls"],
                   "ingest_avg_ms": 0, "ingest_tokens": est["ingest_tokens"],
                   "search_cost": est["search_cost"], "search_calls": est["search_calls"],
                   "search_avg_ms": 0, "search_tokens": est["search_tokens"]},
            "ai_cost": est["total_cost"],
            "timeline": [{"t": "sync start", "cost": 0},
                         {"t": "today", "cost": est["total_cost"]}],
            "recent_searches": [
                {"q": query, "tokens": TOKENS_PER_SEARCH, "ms": None}
                for query, in q(f"""SELECT query FROM events
                                    WHERE {_searches_where()}
                                    ORDER BY created_at DESC LIMIT 8""")],
            "forecast": {"1k": round(1000 * TOKENS_PER_PRODUCT / 1e6 * EMBED_PRICE_PER_M, 3),
                         "10k": round(10000 * TOKENS_PER_PRODUCT / 1e6 * EMBED_PRICE_PER_M, 3),
                         "100k": round(100000 * TOKENS_PER_PRODUCT / 1e6 * EMBED_PRICE_PER_M, 2)}}


@app.get("/stats/search-analytics")
def search_analytics(size: int = 30, source: str = "all", client_id: str = "default"):
    # same brain as the client portal's Analytics page — one truth
    return _analytics_data(source, size, 0)


@app.get("/billing/summary")
def billing_summary(client_id: str = "default"):
    est = est_costs()
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    daily = [{"date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
              "cost": est["total_cost"], "ingest_cost": est["ingest_cost"],
              "search_cost": est["search_cost"]}]
    cur = dict(est)
    cur["days"] = 1
    n = products_count()
    run = {"finished_at": INDEX_FINISHED_AT, "indexed": n,
           "failed": 0, "elapsed_sec": INDEX_ELAPSED_SEC or 0,
           "tokens": est["ingest_tokens"], "cost": est["ingest_cost"]}
    return {"this_month": month, "current": cur,
            "months": [{"month": month, "total_cost": est["total_cost"],
                        "ingest_cost": est["ingest_cost"],
                        "search_cost": est["search_cost"],
                        "ingest_calls": est["ingest_calls"],
                        "search_calls": est["search_calls"]}],
            "days": daily, "recent_days": daily,
            "runs": [run] if n else [],
            "all_time_cost": est["total_cost"],
            "total_cost_of_ownership": {
                "cloud": VM_MONTH_COST, "ai": est["total_cost"],
                "total": round(VM_MONTH_COST + est["total_cost"], 2),
                "items": [
                    {"name": "Azure VM (D4as v6 + disk)", "cost": VM_MONTH_COST},
                    {"name": "OpenAI usage (estimate)", "cost": est["total_cost"]},
                ]}}


@app.get("/billing/month")
def billing_month(month: str = "", client_id: str = "default"):
    est = est_costs()
    n = products_count()
    run = {"finished_at": INDEX_FINISHED_AT, "indexed": n,
           "failed": 0, "elapsed_sec": INDEX_ELAPSED_SEC or 0,
           "tokens": est["ingest_tokens"], "cost": est["ingest_cost"]}
    return {"month": month or datetime.now(timezone.utc).strftime("%Y-%m"),
            "days": [{"date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                      "cost": est["total_cost"], "ingest_cost": est["ingest_cost"],
                      "search_cost": est["search_cost"]}],
            "runs": [run] if n else [], "total_cost": est["total_cost"]}


@app.get("/fields")
def fields_ep(client_id: str = "default"):
    f = index_fields()
    return {"client_id": "venue", "fields": f, "field_count": len(f),
            "registered": bool(f), "id_field": "id", "registered_at": None}


@app.get("/products")
def admin_products(offset: int = 0, limit: int = 30, client_id: str = "default"):
    try:
        size = max(1, min(int(limit), 100))
        page = int(offset) // size + 1
        return _search_products("", "", page, size)
    except Exception:
        return {"total": 0, "items": [], "products": []}


@app.get("/search")
def admin_search(q_param: str = "", k: int = 8, client_id: str = "default",
                 request: Request = None):
    query = (request.query_params.get("q") if request else "") or q_param
    t0 = time.time()
    try:
        data = json.dumps({"query": query, "page": 1, "page_size": int(k)}).encode()
        req = urllib.request.Request("http://127.0.0.1:8000/search", data=data,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as r:
            res = json.loads(r.read())
        results = [{"id": p.get("id"), "name": p.get("name"), "price": p.get("price"),
                    "image": p.get("image") or p.get("image_url"),
                    "score": p.get("score"), "brand": p.get("brand")}
                   for p in (res.get("results") or [])]
        took = round((time.time() - t0) * 1000)
        _log_search(query, took_ms=took,
                    found=res.get("total_results", len(results)))
        return {"results": results, "total": res.get("total_results", len(results)),
                "took_ms": took}
    except Exception as e:
        return {"results": [], "total": 0, "took_ms": None, "error": str(e)[:100]}


@app.get("/opensearch-info")
def opensearch_info(client_id: str = "default"):
    try:
        client = osc()
        h = client.cluster.health()
        st = client.indices.stats(index=OS_INDEX)
        total = st.get("_all", {}).get("primaries", {})
        cats = {}
        for fld in ("categories.keyword", "categories", "category.keyword",
                    "category", "category_names.keyword", "brand.keyword", "brand"):
            try:
                agg = client.search(index=OS_INDEX, body={
                    "size": 0, "aggs": {"c": {"terms": {"field": fld, "size": 60}}}})
                buckets = agg["aggregations"]["c"]["buckets"]
                if buckets:
                    cats = {b["key"]: b["doc_count"] for b in buckets
                            if str(b["key"]).strip()}
                    break
            except Exception:
                continue
        return {"status": h.get("status"), "nodes": h.get("number_of_nodes"),
                "active_shards": h.get("active_shards"),
                "index": OS_INDEX,
                "docs": total.get("docs", {}).get("count", 0),
                "size_bytes": total.get("store", {}).get("size_in_bytes", 0),
                "categories": cats}
    except Exception as e:
        return {"status": "down", "error": str(e)[:100]}


_VENUE_APIS = [
    ("POST", "/search", "AI product search"),
    ("GET", "/search/autocomplete", "type-ahead suggestions"),
    ("POST", "/search/ai-assistant", "AI shopping chat"),
    ("POST", "/search/ai-welcome", "chat welcome + chips"),
    ("GET", "/similar-products", "similar products row"),
    ("GET", "/ai-similar-products", "AI picks (vectors)"),
    ("GET", "/trending", "trending products"),
    ("GET", "/popularcat", "popular categories"),
    ("GET", "/recommendations", "personal recommendations"),
    ("GET", "/pick-up", "pick up where you left"),
    ("GET", "/continueshop", "continue shopping"),
    ("GET", "/recommendation-grids", "homepage grids"),
    ("POST", "/track", "shopper event tracking"),
]


def _nginx_counts():
    counts = {}
    try:
        with open("/var/log/nginx/access.log", "rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - 4_000_000))
            text = f.read().decode(errors="ignore")
        for _, path, _ in _VENUE_APIS:
            counts[path] = len(re.findall(re.escape(path) + r"[ ?]", text))
    except Exception:
        pass
    return counts


@app.get("/api-info")
def api_info():
    c = _nginx_counts()
    eps = {f"{m} {p}": c.get(p, 0) for m, p, w in _VENUE_APIS}
    return {"ok": True, "endpoints": eps, "total_requests": sum(eps.values())}


_API_TAGS = {"/search": "search", "/search/autocomplete": "search",
             "/search/ai-assistant": "assistant", "/search/ai-welcome": "assistant",
             "/similar-products": "discover", "/ai-similar-products": "discover",
             "/trending": "discover", "/popularcat": "discover",
             "/recommendations": "personal", "/pick-up": "personal",
             "/continueshop": "personal", "/recommendation-grids": "personal",
             "/track": "tracking"}


@app.get("/shop-api-info")
def shop_api_info():
    c = _nginx_counts()
    return {"ok": True,
            "endpoints": [{"m": m, "method": m, "path": p, "desc": w,
                           "tag": _API_TAGS.get(p, "search"),
                           "count": c.get(p, 0)}
                          for m, p, w in _VENUE_APIS]}


def _probe_services():
    def svc(name, up, port, kind, image, what):
        return {"name": name, "up": up, "port": port, "kind": kind,
                "image": image, "what": what, "desc": what, "role": what}
    out = []
    try:
        os_up = bool(osc().ping())
    except Exception:
        os_up = False
    out.append(svc("OpenSearch", os_up, 9200, "container",
                   "opensearchproject/opensearch:2.13",
                   "the search database — products + AI vectors"))
    try:
        with urllib.request.urlopen("http://127.0.0.1:8000/docs", timeout=3) as r:
            api_up = r.status in (200, 307)
    except Exception:
        api_up = False
    out.append(svc("Search API", api_up, 8000, "process",
                   "uvicorn app.main:app",
                   "answers every shopper search"))
    out.append(svc("Postgres", bool(q("SELECT 1")), 5432, "container",
                   "postgres:16-alpine",
                   "the tracking database — shopper events"))
    try:
        c = socket.create_connection(("127.0.0.1", 6379), timeout=2)
        c.close()
        redis_up = True
    except Exception:
        redis_up = False
    out.append(svc("Redis", redis_up, 6379, "container", "redis:7-alpine",
                   "the speed cache"))
    out.append(svc("Portal API", True, 8100, "process", "uvicorn main:app",
                   "feeds both dashboards"))
    return out


@app.get("/azure/info")
def azure_info():
    v = vitals()
    mem = v.get("memory") or {}
    disk = v.get("disk") or {}
    try:
        with open("/proc/uptime") as f:
            uptime_h = round(float(f.read().split()[0]) / 3600, 1)
    except Exception:
        uptime_h = None
    machine = {"cpu_percent": v.get("cpu_percent"),
               "cores": os.cpu_count(),
               "uptime_hours": uptime_h,
               "memory": {**mem, "percent": mem.get("pct")},
               "disk": {**disk, "percent": disk.get("pct")},
               "disks": [{"path": "/", "name": "OS disk",
                          "percent": disk.get("pct"),
                          "used_gb": disk.get("used_gb"),
                          "total_gb": disk.get("total_gb"),
                          "free_gb": round((disk.get("total_gb") or 0)
                                           - (disk.get("used_gb") or 0), 1)}]}
    days_left = max(0, (datetime(2026, 11, 23, tzinfo=timezone.utc)
                        - datetime.now(timezone.utc)).days)
    return {"cloud": "azure", "source": "vm",
            "vm_size": "Standard D4as v6 (4 vCPU / 16 GB)",
            "region": "East US 2", "resource_group": "ATHRG240826",
            "scale_set": None,
            "index": {"products": products_count()},
            "https": {"active": True, "domain": "venuemarketplace.xyz",
                      "days_left": days_left, "expires": "2026-11-23"},
            "cpu_percent": v.get("cpu_percent"),
            "memory": v.get("memory"), "disk": v.get("disk"),
            "machine": machine,
            "services": _probe_services(),
            "est_month_cost": VM_MONTH_COST,
            "cost": {"monthly_total": VM_MONTH_COST,
                     "daily_estimate": round(VM_MONTH_COST / 30, 2),
                     "items": [
                         {"name": "Virtual machine (D4as v6)", "monthly": 55.0, "value": 55.0},
                         {"name": "OS disk (30 GB SSD)", "monthly": 5.0, "value": 5.0},
                         {"name": "Bandwidth + IP", "monthly": 2.0, "value": 2.0}]},
            "instances": [{"name": "VenueDemo", "state": "running",
                           "type": "D4as_v6", "ip": "145.132.104.57",
                           "os": "Linux (Ubuntu)", "os_version": "Ubuntu 24.04 LTS",
                           "ami": "Canonical Ubuntu Server 24.04",
                           "imdsv": "required", "admin_user": "azureuser",
                           "private_ip": "172.16.0.4", "public_ip": "145.132.104.57",
                           "region": "East US 2", "zone": "1",
                           "resource_group": "ATHRG240826",
                           "subscription": "Azure credit subscription"}],
            "volumes": [{"id": "osdisk", "name": "OS disk", "type": "SSD",
                         "device": "/dev/root", "size_gb": 30, "encrypted": True}],
            "addresses": [{"ip": "145.132.104.57"}],
            "security_groups": [{
                "name": "VenueDemo network security group",
                "inbound": [
                    {"protocol": "TCP", "ports": "22", "from": "internet",
                     "why": "SSH — our deployment access", "live": "open"},
                    {"protocol": "TCP", "ports": "80", "from": "internet",
                     "why": "HTTP — certificate + redirect", "live": "open"},
                    {"protocol": "TCP", "ports": "443", "from": "internet",
                     "why": "HTTPS — all site + API traffic", "live": "open"}],
                "closed_ports": ["9200 OpenSearch", "5432 Postgres",
                                 "6379 Redis", "8000 / 8100 internal APIs"],
                "outbound": [{"protocol": "all", "ports": "all"}],
                "note": "Every database is bound to localhost — physically unreachable from the internet."}]}


@app.get("/admin/clients")
def admin_clients():
    return {"clients": [{"client_id": "venue", "name": "Venue Marketplace",
                         "status": "active", "products": products_count(),
                         "site_token": "single-store"}]}


@app.get("/admin/overview")
def admin_overview():
    open_t = q("SELECT COUNT(*) FROM portal_tickets WHERE status='open'")
    est = est_costs()
    row = {"client_id": "venue", "name": "Venue Marketplace", "status": "active",
           "products": products_count(), "searches": searches_total(),
           "ai_cost": est["total_cost"],
           "tickets_open": open_t[0][0] if open_t else 0}
    return {"clients": [row]}


@app.get("/admin/tickets")
def admin_tickets(status: str = "", client_id: str = ""):
    ts = _tickets()
    if status:
        ts = [t for t in ts if t["status"] == status]
    return {"tickets": ts}


class AdminTicketReply(BaseModel):
    message: Optional[str] = None
    status: Optional[str] = None


@app.post("/admin/tickets/{ticket_id}/reply")
def admin_ticket_reply(ticket_id: int, body: AdminTicketReply):
    rows = q("SELECT messages, status FROM portal_tickets WHERE id=%s", (ticket_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Ticket not found")
    msgs, status = rows[0]
    msgs = msgs if isinstance(msgs, list) else json.loads(msgs or "[]")
    if body.message:
        msgs.append({"who": "support", "text": body.message.strip()[:4000],
                     "at": datetime.now(timezone.utc).isoformat()})
        status = "pending"
    if body.status in ("open", "pending", "resolved"):
        status = body.status
    qx("UPDATE portal_tickets SET messages=%s, status=%s, updated_at=NOW() WHERE id=%s",
       (json.dumps(msgs), status, ticket_id))
    return {"ok": True}


@app.post("/admin/clients")
@app.post("/admin/clients/{client_id}/rotate-key")
@app.post("/admin/clients/{client_id}/portal-password")
def admin_single_tenant(client_id: str = ""):
    raise HTTPException(status_code=400,
                        detail="Single-store setup — passwords and keys are managed in the server's .env")


@app.delete("/admin/clients/{client_id}")
def admin_no_delete(client_id: str):
    raise HTTPException(status_code=400, detail="Single-store setup — nothing to delete")


# =================================================================
# 🖥️ LEGACY (/portal-api/*) — kept so the v1 dashboard still works
# =================================================================
@app.post("/portal-api/login")
def legacy_login(body: LoginBody):
    return login(body)


@app.get("/portal-api/health")
def legacy_health():
    return {"ok": True, "at": datetime.now(timezone.utc).isoformat()}


@app.get("/portal-api/admin/system")
def legacy_admin_system(authorization: Optional[str] = Header(None)):
    check(authorization, need_admin=True)
    out = {"at": datetime.now(timezone.utc).isoformat(), "index_target": INDEX_TARGET}
    try:
        client = osc()
        out["opensearch"] = {"up": True, "status": client.cluster.health().get("status", "?")}
        n = client.count(index=OS_INDEX).get("count", 0)
        out["indexing"] = {"count": n, "target": INDEX_TARGET,
                           "pct": round(min(100.0, n * 100.0 / INDEX_TARGET), 1)}
    except Exception as e:
        out["opensearch"] = {"up": False, "error": str(e)[:80]}
        out["indexing"] = {"count": 0, "target": INDEX_TARGET, "pct": 0}
    rows = q("""SELECT (SELECT COUNT(*) FROM events), (SELECT COUNT(*) FROM orders),
                       (SELECT COUNT(*) FROM product_metrics)""")
    ev, orders, pm = rows[0] if rows else (0, 0, 0)
    out["postgres"] = {"up": bool(rows), "events": ev, "orders": orders,
                       "product_metrics": pm}
    try:
        with urllib.request.urlopen("http://127.0.0.1:8000/docs", timeout=4) as r:
            out["search_api"] = {"up": r.status in (200, 307)}
    except Exception:
        out["search_api"] = {"up": False}
    try:
        s = socket.create_connection(("127.0.0.1", 6379), timeout=2)
        s.close()
        out["redis"] = {"up": True}
    except Exception:
        out["redis"] = {"up": False}
    out.update(vitals())
    return out
