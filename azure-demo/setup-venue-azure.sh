#!/bin/bash
# =====================================================================
# 🚀 VENUE AI SEARCH — Azure VM bootstrap (mirror of the AWS EC2
# user_data, Azure edition). Run as: sudo bash setup-venue-azure.sh
# Idempotent: safe to re-run.
# =====================================================================
set -e
DOMAIN="venuemarketplace.xyz"
REPO="https://github.com/ath-ai-search/ai-search-backend.git"
# ⚠️ the FROZEN backend code (scripts/pipeline.py + stats/search services)
# has this exact password built in as its default — the container MUST match
# it or trending/stats silently break. Safe: 5432 is loopback-only + NSG.
# Pass the SAME PG_PW on every re-run (postgres keeps the first-init password).
PG_PW="${PG_PW:-shubham16}"

echo "=== System prep ==="
apt-get update -y
apt-get install -y python3 python3-pip python3-venv git curl unzip nginx \
  ca-certificates gnupg tmux certbot python3-certbot-nginx
# demo audience is IST — keeps "x seconds ago" on the portal truthful
timedatectl set-timezone Asia/Kolkata || true

echo "=== Docker ==="
if ! command -v docker >/dev/null; then
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
    https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -y
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
fi

echo "=== Containers: OpenSearch + Postgres + Redis ==="
RAM_GB=$(awk '/MemTotal/ {printf "%d", $2/1024/1024}' /proc/meminfo)
HEAP=$(( RAM_GB >= 24 ? 8 : RAM_GB >= 12 ? 4 : 2 ))g
# 127.0.0.1 bindings: docker -p bypasses ufw, and OpenSearch runs with
# security disabled — nothing off-box ever needs these three ports
docker rm -f venue-opensearch venue-postgres venue-redis 2>/dev/null || true
docker run -d --name venue-opensearch --restart always -p 127.0.0.1:9200:9200 \
  -e discovery.type=single-node -e plugins.security.disabled=true \
  -e OPENSEARCH_INITIAL_ADMIN_PASSWORD='LocalOnly_Str0ng!123' \
  -e "OPENSEARCH_JAVA_OPTS=-Xms${HEAP} -Xmx${HEAP}" \
  -v venue-os-data:/usr/share/opensearch/data \
  opensearchproject/opensearch:2.13.0
docker run -d --name venue-postgres --restart always -p 127.0.0.1:5432:5432 \
  -e POSTGRES_PASSWORD="${PG_PW}" -e POSTGRES_DB=venue_ai \
  -e TZ=Asia/Kolkata -e PGTZ=Asia/Kolkata \
  -v venue-pg-data:/var/lib/postgresql/data postgres:16-alpine
docker run -d --name venue-redis --restart always -p 127.0.0.1:6379:6379 \
  -v venue-redis-data:/data redis:7-alpine

echo "=== Local TLS shim for OpenSearch (this is what replaces the code patch) ==="
# WHY: the frozen backend builds its OpenSearch client with
#   hosts=[{'host': HOST, 'port': 443}], use_ssl=True, verify_certs=True
# and AWS SigV4 auth -- all hard-coded. We cannot edit the code, so instead we
# GIVE it exactly what it expects: a trusted TLS endpoint on localhost:443.
# nginx terminates TLS there and forwards to OpenSearch on 9200. OpenSearch
# runs with security disabled, so the AWS signature header is simply ignored.
CERT_DIR=/etc/nginx/venue-os
mkdir -p "$CERT_DIR"
if [ ! -f "$CERT_DIR/cert.pem" ]; then
  cat > "$CERT_DIR/openssl.cnf" <<'OSSL'
[req]
distinguished_name = dn
x509_extensions = v3
prompt = no
[dn]
CN = localhost
[v3]
subjectAltName = DNS:localhost,IP:127.0.0.1
basicConstraints = critical,CA:TRUE
OSSL
  openssl req -x509 -newkey rsa:2048 -nodes -days 3650     -keyout "$CERT_DIR/key.pem" -out "$CERT_DIR/cert.pem"     -config "$CERT_DIR/openssl.cnf"
  chmod 600 "$CERT_DIR/key.pem"
fi

# SNI-routed: this block only answers to the name "localhost", so the public
# venue site can keep its own 443 block on the same port with its own cert.
cat > /etc/nginx/sites-available/venue-opensearch <<NGINX
server {
    listen 443 ssl;
    server_name localhost;

    ssl_certificate     $CERT_DIR/cert.pem;
    ssl_certificate_key $CERT_DIR/key.pem;

    # never reachable from outside the VM
    allow 127.0.0.1;
    deny  all;

    # bulk indexing sends multi-MB bodies and long-running requests
    client_max_body_size 0;
    proxy_read_timeout   600s;
    proxy_send_timeout   600s;

    location / {
        proxy_pass http://127.0.0.1:9200;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
    }
}
NGINX
ln -sf /etc/nginx/sites-available/venue-opensearch /etc/nginx/sites-enabled/venue-opensearch
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx
echo ">>> OpenSearch reachable at https://localhost:443 (cert: $CERT_DIR/cert.pem)"

echo "=== Repo -> /opt/pipeline (same path as EC2, code untouched) ==="
if [ ! -d /opt/pipeline/.git ]; then
  git clone "$REPO" /opt/pipeline
fi

echo "=== Python venv (exact EC2 pip list + psycopg2 + sqlalchemy for tracking) ==="
python3 -m venv /opt/pipeline/venv
/opt/pipeline/venv/bin/pip install --upgrade pip
/opt/pipeline/venv/bin/pip install httpx python-dotenv opensearch-py boto3 \
  asyncio fastapi uvicorn requests-aws4auth pydantic redis openai \
  sqlalchemy psycopg2-binary requests

echo "=== Restore tracking DB (latest_backup.sql if present) ==="
if [ -f /opt/pipeline/latest_backup.sql ]; then
  sleep 8
  docker exec -i venue-postgres psql -U postgres venue_ai \
    < /opt/pipeline/latest_backup.sql || echo "restore skipped/partial (ok if tables exist)"
fi

echo "=== .env skeleton (FILL THE REAL VALUES, see DEMO-PLAN step 3) ==="
mkdir -p /opt/pipeline/api
if [ ! -f /opt/pipeline/api/.env ]; then
cat > /opt/pipeline/api/.env <<ENV
BIGCOMMERCE_STORE_HASH=FILL_ME
BIGCOMMERCE_ACCESS_TOKEN=FILL_ME
BIGCOMMERCE_CLIENT_ID=FILL_ME
OPENAI_API_KEY=FILL_ME
# ⚠️ HOST ONLY - no ":9200". The frozen code appends port 443 itself, and
# our nginx TLS shim is listening there. Adding a port here breaks it.
OPENSEARCH_HOST=localhost
OPENSEARCH_INDEX=products
OPENSEARCH_REGION=us-west-2
# the code calls boto3 for AWS SigV4 before it ever opens a socket; with no
# credentials it raises at import. These are never sent anywhere real -
# OpenSearch has security disabled and ignores the signature.
AWS_ACCESS_KEY_ID=localonlydummykey000
AWS_SECRET_ACCESS_KEY=localonlydummysecret00000000000000000000
AWS_DEFAULT_REGION=us-west-2
# verify_certs=True is hard-coded, so point requests at our self-signed cert
REQUESTS_CA_BUNDLE=/etc/nginx/venue-os/cert.pem
REDIS_URL=redis://localhost:6379
DATABASE_URL=postgresql://postgres:${PG_PW}@localhost:5432/venue_ai
DB_HOST=localhost
DB_PORT=5432
DB_NAME=venue_ai
DB_USER=postgres
DB_PASSWORD=${PG_PW}
ENV
  echo ">>> postgres password written into .env: ${PG_PW}"
fi
# ⚠️ scripts/pipeline.py (and all backfill scripts) read /opt/pipeline/.env,
# NOT api/.env — keep the two files identical, and re-copy after ANY edit
cp -f /opt/pipeline/api/.env /opt/pipeline/.env

echo "=== systemd service (identical to EC2) ==="
cat > /etc/systemd/system/search-api.service <<'SERVICE'
[Unit]
Description=FastAPI Search Service
After=network.target docker.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/pipeline/api
EnvironmentFile=/opt/pipeline/api/.env
ExecStart=/opt/pipeline/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICE
systemctl daemon-reload
systemctl enable search-api.service
systemctl restart search-api.service || true

echo "=== Venue client portal (separate service — backend code untouched) ==="
# The portal ships INSIDE this repo — auto-install from the clone.
# (Manual copy to /opt/venue-portal still works as a fallback.)
mkdir -p /opt/venue-portal/api /opt/venue-portal/dist
if [ -f /opt/pipeline/venue-portal-api/main.py ]; then
  cp -f /opt/pipeline/venue-portal-api/main.py         /opt/pipeline/venue-portal-api/requirements.txt /opt/venue-portal/api/
fi
if [ -f /opt/pipeline/venue-client-dashboard/dist/index.html ]; then
  cp -rf /opt/pipeline/venue-client-dashboard/dist/. /opt/venue-portal/dist/
fi
if [ -f /opt/venue-portal/api/main.py ]; then
  python3 -m venv /opt/venue-portal/venv
  /opt/venue-portal/venv/bin/pip install --upgrade pip
  /opt/venue-portal/venv/bin/pip install -r /opt/venue-portal/api/requirements.txt
  if [ ! -f /opt/venue-portal/api/.env ]; then
cat > /opt/venue-portal/api/.env <<PENV
DATABASE_URL=postgresql://postgres:${PG_PW}@localhost:5432/venue_ai
OPENSEARCH_HOST=localhost:9200
OPENSEARCH_INDEX=products
OPENAI_API_KEY=FILL_ME
AI_CHAT_MODEL=gpt-4o-mini
PORTAL_PASSWORD=FILL_ME
ADMIN_PASSWORD=FILL_ME
INDEX_TARGET=270332
PORTAL_SECRET=$(openssl rand -hex 24)
PENV
    echo ">>> fill OPENAI_API_KEY + PORTAL_PASSWORD + ADMIN_PASSWORD in /opt/venue-portal/api/.env"
  fi
cat > /etc/systemd/system/venue-portal.service <<'SERVICE'
[Unit]
Description=Venue Client Portal API
After=network.target docker.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/venue-portal/api
ExecStart=/opt/venue-portal/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8100
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICE
  systemctl daemon-reload
  systemctl enable venue-portal.service
  systemctl restart venue-portal.service || true
else
  echo ">>> portal files not copied yet — skipping (re-run after copying)"
fi

echo "=== nginx: the API on the venue domain ==="
cat > /etc/nginx/sites-available/venue <<NGINX
server {
    listen 80;
    server_name ${DOMAIN} www.${DOMAIN};

    # the API surface the venue website + demo use
    location ~ ^/(docs|openapi.json|search|autocomplete|widget|similar-products|ai-similar-products|trending|popularcat|recommendations|pick-up|continueshop|recommendation-grids|track)($|/) {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }

    # client portal — dashboard (static build) + its own read-only API
    location = /portal { return 301 /portal/; }
    location /portal/ {
        alias /opt/venue-portal/dist/;
        try_files \$uri \$uri/ /portal/index.html;
    }
    location /portal-api/ {
        proxy_pass http://127.0.0.1:8100;
        proxy_set_header Host \$host;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }

    # the venue website build, if we host it here (else returns a holding page)
    root /opt/site;
    index index.html;
    location / { try_files \$uri \$uri/ /index.html; }
}
NGINX
mkdir -p /opt/site
[ -f /opt/site/index.html ] || echo "<h1>Venue Marketplace</h1>" > /opt/site/index.html
ln -sf /etc/nginx/sites-available/venue /etc/nginx/sites-enabled/venue
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

echo "=== HTTPS (run AFTER the DNS points here) ==="
echo "    sudo apt-get install -y certbot python3-certbot-nginx"
echo "    sudo certbot --nginx -d ${DOMAIN} -d www.${DOMAIN} -m pradeep.kumar@athinfosys.com --agree-tos -n"

echo ""
echo "=== DONE. NO CODE PATCH NEEDED - the TLS shim replaces it."
echo "    Next: fill the real keys in /opt/pipeline/api/.env, then:"
echo "      sudo cp /opt/pipeline/api/.env /opt/pipeline/.env"
echo "      sudo systemctl restart search-api"
echo "    Verify the shim before indexing (must print a version number):"
echo "      curl --cacert /etc/nginx/venue-os/cert.pem https://localhost/"
echo "    ⚠️ AFTER any .env edit: sudo cp /opt/pipeline/api/.env /opt/pipeline/.env"
echo "    Index run (INSIDE tmux — hours long, must not die with SSH):"
echo "      tmux new -s pipeline"
echo "      cd /opt/pipeline && sudo ./venv/bin/python scripts/pipeline.py 2>&1 | tee ~/pipeline.log"
echo "      (detach: Ctrl-b then d · reattach: tmux attach -t pipeline)"
echo "    ⚠️ NEVER re-run this setup script while pipeline.py is running"
echo "    Portal: fill /opt/venue-portal/api/.env then: sudo systemctl restart venue-portal"
echo "    Portal URL: https://${DOMAIN}/portal/  (sign in: venue + PORTAL_PASSWORD)"
