"""
=====================================================================================
🧑‍💼 VENUE CLIENT PORTAL — API  (a SEPARATE service; ai-search-backend untouched)
=====================================================================================
Reads the data the backend already produces — nothing is written back:
  • Postgres `venue_ai`  → events / orders / product_metrics (the /track output)
  • OpenSearch `products`→ the indexed catalogue
Serves the venue-client-dashboard frontend. Run:
  uvicorn main:app --host 0.0.0.0 --port 8100
Env (.env next to this file):
  DATABASE_URL, OPENSEARCH_HOST (host:port, local), OPENSEARCH_INDEX,
  OPENAI_API_KEY (for blu), PORTAL_PASSWORD, PORTAL_SECRET
=====================================================================================
"""

import base64
import hashlib
import hmac
import json
import os
import time
from datetime import datetime, timezone
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/venue_ai")
OS_HOST = os.getenv("OPENSEARCH_HOST", "localhost:9200")
OS_INDEX = os.getenv("OPENSEARCH_INDEX", "products")
PORTAL_PASSWORD = os.getenv("PORTAL_PASSWORD", "")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
INDEX_TARGET = int(os.getenv("INDEX_TARGET", "270332"))
SECRET = (os.getenv("PORTAL_SECRET") or "venue-portal-dev-secret").encode()
CLIENT = {"client_id": "venue", "name": "Venue Marketplace"}

app = FastAPI(title="Venue Client Portal API", docs_url=None, redoc_url=None)
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
            return cur.fetchall()
    except Exception:
        return []


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


@app.post("/portal-api/login")
def login(body: LoginBody):
    now = time.time()
    _fails[:] = [t for t in _fails if now - t < 600]
    if len(_fails) >= 8:
        raise HTTPException(status_code=429, detail="Too many attempts — wait 10 minutes")
    who = body.client_id.strip().lower()
    # 👑 admin signs in at the same door with id "admin" + ADMIN_PASSWORD
    if who == "admin" and ADMIN_PASSWORD \
            and hmac.compare_digest(body.password, ADMIN_PASSWORD):
        return {"token": issue_token(role="admin"),
                "client": {**CLIENT, "role": "admin", "name": "Venue Admin"}}
    if who != "venue" or not PORTAL_PASSWORD \
            or not hmac.compare_digest(body.password, PORTAL_PASSWORD):
        _fails.append(now)
        raise HTTPException(status_code=401, detail="Wrong client id or password")
    return {"token": issue_token(), "client": {**CLIENT, "role": "client"}}


# ---------------------------------------------------------------- endpoints
@app.get("/portal-api/me")
def me(authorization: Optional[str] = Header(None)):
    check(authorization)
    products = 0
    try:
        products = osc().count(index=OS_INDEX).get("count", 0)
    except Exception:
        pass
    last = q("SELECT MAX(created_at) FROM events")
    return {**CLIENT, "products": products,
            "doctor": {"last_event_at": str(last[0][0]) if last and last[0][0] else None}}


@app.get("/portal-api/overview")
def overview(authorization: Optional[str] = Header(None)):
    check(authorization)
    products = 0
    try:
        products = osc().count(index=OS_INDEX).get("count", 0)
    except Exception:
        pass
    counts = dict(q("""SELECT event_type, COUNT(*) FROM events GROUP BY event_type"""))
    today = dict(q("""SELECT event_type, COUNT(*) FROM events
                      WHERE created_at::date = CURRENT_DATE GROUP BY event_type"""))
    revenue = q("""SELECT COALESCE(SUM(value),0) FROM events
                   WHERE event_type='purchase'""")
    rev_month = q("""SELECT COALESCE(SUM(value),0) FROM events
                     WHERE event_type='purchase'
                     AND date_trunc('month', created_at) = date_trunc('month', now())""")
    queries = q("""SELECT COUNT(DISTINCT query) FROM events
                   WHERE query IS NOT NULL AND query <> ''""")
    daily = q("""SELECT created_at::date::text,
                        COUNT(*) FILTER (WHERE event_type='click'),
                        COUNT(*) FILTER (WHERE event_type='purchase'),
                        COUNT(*) FILTER (WHERE event_type='impression')
                 FROM events WHERE created_at > now() - interval '14 days'
                 GROUP BY 1 ORDER BY 1"""
             )
    top = q("""SELECT query, COUNT(*) FILTER (WHERE event_type='click') c,
                      COUNT(*) FILTER (WHERE event_type='purchase') p,
                      COALESCE(SUM(value) FILTER (WHERE event_type='purchase'),0)
               FROM events WHERE query IS NOT NULL AND query <> ''
               GROUP BY query ORDER BY c DESC LIMIT 8""")
    live = q("SELECT COUNT(*) FROM events WHERE created_at > now() - interval '5 minutes'")
    return {
        "products": products,
        "clicks_total": counts.get("click", 0),
        "carts_total": counts.get("add_to_cart", 0),
        "orders_total": counts.get("purchase", 0),
        "impressions_total": counts.get("impression", 0),
        "queries_total": queries[0][0] if queries else 0,
        "revenue_total": float(revenue[0][0]) if revenue else 0.0,
        "revenue_month": float(rev_month[0][0]) if rev_month else 0.0,
        "today": {k: v for k, v in today.items()},
        "live_5m": live[0][0] if live else 0,
        "daily": [{"date": d, "clicks": c, "orders": p, "impressions": i}
                  for d, c, p, i in daily],
        "top": [{"query": t, "clicks": c, "orders": p, "revenue": float(r)}
                for t, c, p, r in top],
    }


@app.get("/portal-api/events")
def events(type: Optional[str] = None, size: int = 60,
           authorization: Optional[str] = Header(None)):
    check(authorization)
    size = max(1, min(int(size or 60), 200))
    flt, args = "", []
    if type and type != "all":
        flt, args = "WHERE event_type = %s", [type]
    else:
        flt = "WHERE event_type <> 'impression'"
    rows = q(f"""SELECT event_type, COALESCE(query,''), COALESCE(product_id,''),
                        COALESCE(value,0), created_at
                 FROM events {flt} ORDER BY created_at DESC LIMIT %s""", args + [size])
    counts = dict(q("SELECT event_type, COUNT(*) FROM events GROUP BY event_type"))
    return {"counts": counts,
            "recent": [{"type": t, "query": qq, "product_id": pid,
                        "value": float(v or 0), "at": str(at)}
                       for t, qq, pid, v, at in rows]}


@app.get("/portal-api/trending")
def trending(authorization: Optional[str] = Header(None)):
    check(authorization)
    rows = q("""SELECT product_id, SUM(clicks), SUM(carts), SUM(purchases),
                       SUM(trending_score)
                FROM product_metrics GROUP BY product_id
                ORDER BY SUM(trending_score) DESC NULLS LAST LIMIT 10""")
    out = []
    for pid, clicks, carts, buys, score in rows:
        name = pid
        try:
            doc = osc().get(index=OS_INDEX, id=pid)["_source"]
            name = doc.get("name") or pid
        except Exception:
            pass
        out.append({"product_id": pid, "name": name, "clicks": int(clicks or 0),
                    "carts": int(carts or 0), "purchases": int(buys or 0),
                    "score": float(score or 0)})
    return {"trending": out}


@app.get("/portal-api/products")
def products(qq: str = "", page: int = 1, size: int = 24,
             authorization: Optional[str] = Header(None)):
    check(authorization)
    page, size = max(1, min(page, 500)), max(1, min(size, 100))
    body = {"from": (page - 1) * size, "size": size,
            "_source": {"excludes": ["embedding", "vector", "embeddings"]},
            "track_total_hits": True,
            "query": ({"multi_match": {"query": qq, "fields": ["name^3", "brand", "categories"],
                                       "fuzziness": "AUTO"}} if qq else {"match_all": {}})}
    try:
        res = osc().search(index=OS_INDEX, body=body)
        return {"total": res["hits"]["total"]["value"],
                "items": [h["_source"] | {"_id": h["_id"]} for h in res["hits"]["hits"]]}
    except Exception:
        return {"total": 0, "items": []}


class AskBody(BaseModel):
    question: str = Field(min_length=1, max_length=500)


@app.post("/portal-api/assistant")
def assistant(body: AskBody, authorization: Optional[str] = Header(None)):
    check(authorization)
    ground = overview(authorization)
    system = (
        "You are blu, the assistant inside the Venue Marketplace search dashboard. "
        "Answer ONLY from the JSON below about THIS store; refuse anything else in one "
        "sentence. Never invent numbers; money is USD. 2-3 short sentences.\n"
        "Reply as STRICT JSON: {\"answer\": \"...\", \"followups\": [up to 3 short "
        "related questions]}.\n\nSTORE DATA:\n" + json.dumps(ground)[:6000])
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
        model = os.getenv("AI_CHAT_MODEL", "gpt-4o-mini")
        kwargs = ({"max_completion_tokens": 2000}
                  if model.startswith(("gpt-5", "o1", "o3", "o4"))
                  else {"temperature": 0.3, "max_tokens": 400})
        r = client.chat.completions.create(model=model,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": body.question.strip()}],
            response_format={"type": "json_object"}, **kwargs)
        obj = json.loads(r.choices[0].message.content or "{}")
        return {"answer": str(obj.get("answer") or "").strip() or "…",
                "followups": [str(f)[:120] for f in (obj.get("followups") or [])][:3]}
    except Exception:
        raise HTTPException(status_code=503,
                            detail="blu is having trouble thinking — try again in a moment")


# ---------------------------------------------------------------- admin only
@app.get("/portal-api/admin/system")
def admin_system(authorization: Optional[str] = Header(None)):
    """👑 One call = full machine-room view. Read-only, admin token only."""
    check(authorization, need_admin=True)
    out = {"at": datetime.now(timezone.utc).isoformat(), "index_target": INDEX_TARGET}

    # OpenSearch + indexing progress
    try:
        client = osc()
        out["opensearch"] = {"up": True,
                             "status": client.cluster.health().get("status", "?")}
        n = client.count(index=OS_INDEX).get("count", 0)
        out["indexing"] = {"count": n, "target": INDEX_TARGET,
                           "pct": round(min(100.0, n * 100.0 / INDEX_TARGET), 1)}
    except Exception as e:
        out["opensearch"] = {"up": False, "error": str(e)[:80]}
        out["indexing"] = {"count": 0, "target": INDEX_TARGET, "pct": 0}

    # Postgres + table counts
    try:
        rows = q("""SELECT (SELECT COUNT(*) FROM events),
                           (SELECT COUNT(*) FROM orders),
                           (SELECT COUNT(*) FROM product_metrics)""")
        ev, orders, pm = rows[0] if rows else (0, 0, 0)
        out["postgres"] = {"up": bool(rows), "events": ev, "orders": orders,
                           "product_metrics": pm}
    except Exception as e:
        out["postgres"] = {"up": False, "error": str(e)[:80]}

    # search API + redis — plain socket/HTTP checks, nothing invasive
    import socket
    import urllib.request
    try:
        with urllib.request.urlopen("http://127.0.0.1:8000/docs", timeout=4) as r:
            out["search_api"] = {"up": r.status in (200, 307)}
    except Exception as e:
        out["search_api"] = {"up": False, "error": str(e)[:60]}
    try:
        s = socket.create_connection(("127.0.0.1", 6379), timeout=2)
        s.close()
        out["redis"] = {"up": True}
    except Exception:
        out["redis"] = {"up": False}

    # machine vitals
    try:
        import shutil
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
    return out


@app.get("/portal-api/health")
def health():
    return {"ok": True, "at": datetime.now(timezone.utc).isoformat()}
