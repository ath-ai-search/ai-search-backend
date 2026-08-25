#!/bin/bash
# =====================================================================
# 🌐 VENUE SUBDOMAINS — portal.venuemarketplace.xyz (client portal) and
# admin.venuemarketplace.xyz (admin console, basic-auth shielded).
# Run AFTER setup-venue-azure.sh, from the updated /opt/pipeline clone:
#   sudo bash /opt/pipeline/azure-demo/setup-subdomains.sh
# Idempotent. Does NOT touch the running pipeline or search-api.
# =====================================================================
set -e
DOMAIN="venuemarketplace.xyz"
REPO=/opt/pipeline
PORTAL=/opt/venue-portal

echo "=== deps ==="
apt-get install -y apache2-utils >/dev/null

echo "=== portal API v2 (same service, richer brain) ==="
cp -f "$REPO/venue-portal-api/main.py" "$PORTAL/api/main.py"
cp -f "$REPO/venue-portal-api/requirements.txt" "$PORTAL/api/requirements.txt"
"$PORTAL/venv/bin/pip" install -q -r "$PORTAL/api/requirements.txt"

echo "=== dashboards ==="
mkdir -p "$PORTAL/dist-client" "$PORTAL/dist-admin"
if [ -f "$REPO/venue-client-dashboard-v2/dist/index.html" ]; then
  cp -rf "$REPO/venue-client-dashboard-v2/dist/." "$PORTAL/dist-client/"
else
  echo "!! client dashboard dist missing — push/pull it first"; exit 1
fi
if [ -f "$REPO/venue-admin-dashboard/dist/index.html" ]; then
  cp -rf "$REPO/venue-admin-dashboard/dist/." "$PORTAL/dist-admin/"
else
  echo "!! admin dashboard dist missing — push/pull it first"; exit 1
fi

echo "=== retire the OLD /portal/ page (redirect to the new portal) ==="
cat > "$PORTAL/dist/index.html" <<'HTML'
<!doctype html><meta charset="utf-8">
<meta http-equiv="refresh" content="0; url=https://portal.venuemarketplace.xyz/">
<title>Moved</title>
<p>The portal moved to <a href="https://portal.venuemarketplace.xyz/">portal.venuemarketplace.xyz</a></p>
HTML
find "$PORTAL/dist" -mindepth 1 ! -name index.html -delete 2>/dev/null || true

echo "=== admin web shield (basic auth on top of everything) ==="
if [ ! -f /etc/nginx/.htpasswd-venue-admin ]; then
  ADMIN_WEB_PW=$(openssl rand -base64 12 | tr -dc 'A-Za-z0-9' | cut -c1-12)
  htpasswd -bc /etc/nginx/.htpasswd-venue-admin venueadmin "$ADMIN_WEB_PW"
  echo ">>> ADMIN WEB LOGIN (browser popup): venueadmin / $ADMIN_WEB_PW  — WRITE IT DOWN"
else
  echo ">>> admin web login already exists (delete /etc/nginx/.htpasswd-venue-admin to reset)"
fi

echo "=== nginx: the two subdomains ==="
cat > /etc/nginx/sites-available/venue-portal-sub <<NGINX
server {
    listen 80;
    server_name portal.${DOMAIN};

    root ${PORTAL}/dist-client;
    index index.html;
    location / { try_files \$uri \$uri/ /index.html; }

    location /client-api/ {
        proxy_pass http://127.0.0.1:8100;
        proxy_set_header Host \$host;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }
}

server {
    listen 80;
    server_name admin.${DOMAIN};

    auth_basic           "Venue Admin";
    auth_basic_user_file /etc/nginx/.htpasswd-venue-admin;

    root ${PORTAL}/dist-admin;
    index index.html;
    location / { try_files \$uri \$uri/ /index.html; }

    # every data path the admin console calls
    location ~ ^/(stats|billing|fields|products|search|opensearch-info|api-info|shop-api-info|azure|health|admin|client-api)(/|\$|\?) {
        auth_basic           "Venue Admin";
        auth_basic_user_file /etc/nginx/.htpasswd-venue-admin;
        proxy_pass http://127.0.0.1:8100;
        proxy_set_header Host \$host;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }
}
NGINX
ln -sf /etc/nginx/sites-available/venue-portal-sub /etc/nginx/sites-enabled/venue-portal-sub
nginx -t && systemctl reload nginx

echo "=== restart portal API ==="
systemctl restart venue-portal

echo "=== HTTPS for the new names (DNS must already point here) ==="
certbot --nginx -d ${DOMAIN} -d www.${DOMAIN} -d portal.${DOMAIN} -d admin.${DOMAIN} \
  --agree-tos --register-unsafely-without-email -n --expand \
  || echo "!! certbot failed — check that portal./admin. DNS resolve to this VM, then re-run"

echo ""
echo "=== DONE ==="
echo "  Client portal : https://portal.${DOMAIN}   (login: venue / PORTAL_PASSWORD)"
echo "  Admin console : https://admin.${DOMAIN}    (browser popup: venueadmin + the password above,"
echo "                                              then the console loads directly)"
echo "  Old path      : https://${DOMAIN}/portal/  (still works)"
