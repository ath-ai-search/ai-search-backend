# 🎯 Venue AI Search — Azure demo plan (deadline: tomorrow)

The AWS EC2 died (unpaid bill). We rebuild the SAME system on one Azure VM,
same code, same domain (venuemarketplace.xyz), and index from BigCommerce.

---

## ✅ VM RECEIVED 2026-08-24 (from Meha Ma'am)
IP **20.219.141.225** · user **venueDemo** (password in her email) · resource
group venueDemo · E4as_v4 (4 vCPU / 32 GB) · Ubuntu 24.04 · Central India.
Preflight facts checked the same day: the GitHub repo is PUBLIC (clone works
from the VM), root DNS A still points to the dead AWS IP 44.244.9.52 (site is
ALREADY down — switching DNS breaks nothing), `www` is a CNAME to root (needs
no change), api.venuemarketplace.xyz does not exist.

## STEP 0 — confirm with the cloud team (three yes/no questions)
1. NSG inbound = ONLY 22, 80, 443 — nothing else. And port 22 allowed from
   WHERE? (if "our IP only", it must be the laptop's CURRENT public IP)
   Port 80 must be open to ALL (certbot needs it), not IP-restricted.
2. Is the public IP allocation **Static**? (Dynamic changes on restart → kills DNS)
3. What disk size? (we asked 256 GB; a default 30 GB is too tight for 330k
   products + Docker) — check yourself after login: `df -h`

## STEP 1 — DNS, FIRST THING (it needs time to spread)
Whoever controls venuemarketplace.xyz (GoDaddy): change A record `@` →
**20.219.141.225**. `www` follows automatically (CNAME). The site is already
dead, so this cannot break anything. TTL is 600s — fast.
Check from the laptop until it flips:  nslookup venuemarketplace.xyz 8.8.8.8

## STEP 2 — On the new VM: one script does everything
    scp -r C:\venue\ath\ath\azure-demo  venueDemo@20.219.141.225:~
    ssh venueDemo@20.219.141.225
    sudo PG_PW=shubham16 bash ~/azure-demo/setup-venue-azure.sh

(PG_PW **must** be shubham16 — the frozen backend code has it built in as its
default; the script now uses it automatically, passing it is belt-and-braces.
Pass the same on EVERY re-run.)

What the script installs (mirror of the old EC2 user_data, Azure edition):
- Docker + containers on **127.0.0.1 only**: OpenSearch 2.13 (security off,
  heap 8g on 32 GB), Postgres 16 (restores latest_backup.sql, IST timezone),
  Redis 7
- Python venv (exact EC2 pip list), repo cloned to **/opt/pipeline**
- systemd `search-api` :8000, nginx routes, tmux + certbot installed
- VM timezone set to Asia/Kolkata (so portal "seconds ago" is truthful)

## STEP 3 — the .env  (⚠️ TWO files, not one)
Copy the real keys up (file transfer only — values never typed/shown):

    scp C:\venue\ath\ath\ai-search-backend\.env venueDemo@20.219.141.225:~/venue-old.env

On the VM, build api/.env = real keys + the local-mode lines, then MIRROR it:

    sudo bash -c 'grep -E "^(BIGCOMMERCE_STORE_HASH|BIGCOMMERCE_ACCESS_TOKEN|BIGCOMMERCE_CLIENT_ID|OPENAI_API_KEY)=" /home/venueDemo/venue-old.env > /opt/pipeline/api/.env'
    sudo tee -a /opt/pipeline/api/.env >/dev/null <<'EOF'
    OPENSEARCH_HOST=localhost
    OPENSEARCH_INDEX=products
    OPENSEARCH_REGION=us-west-2
    AWS_ACCESS_KEY_ID=localonlydummykey000
    AWS_SECRET_ACCESS_KEY=localonlydummysecret00000000000000000000
    AWS_DEFAULT_REGION=us-west-2
    REQUESTS_CA_BUNDLE=/etc/nginx/venue-os/cert.pem
    REDIS_URL=redis://localhost:6379
    DATABASE_URL=postgresql://postgres:shubham16@localhost:5432/venue_ai
    DB_HOST=localhost
    DB_PORT=5432
    DB_NAME=venue_ai
    DB_USER=postgres
    DB_PASSWORD=shubham16
    EOF
    sudo cp /opt/pipeline/api/.env /opt/pipeline/.env   # ← scripts read THIS one
    rm /home/venueDemo/venue-old.env

WHY two files: `api/app/config.py` hard-codes `/opt/pipeline/api/.env`, but
`scripts/pipeline.py` (and every backfill script) does a bare `load_dotenv()`
that finds `/opt/pipeline/.env`. If they differ, indexing runs in AWS mode
and dies. After ANY later .env edit, repeat the `cp`. Verify both are ready:

    grep -c REQUESTS_CA_BUNDLE /opt/pipeline/.env /opt/pipeline/api/.env  # both must say 1

⚠️ `OPENSEARCH_HOST` is the bare host — **no `:9200`**. The frozen code adds
port 443 itself, and our TLS shim is listening there. Adding a port breaks it.

## STEP 4 — ✅ NO CODE PATCH NEEDED (tested 2026-08-24)
CEO's "no code changes" is honoured **100%** — `ai-search-backend` is not
touched at all. Earlier we thought a patch was unavoidable; it is not.

The code hard-codes `port: 443`, `use_ssl=True`, `verify_certs=True` and AWS
SigV4 auth. Instead of changing that, the setup script now GIVES it exactly
what it expects, on the VM itself:

  1. nginx terminates TLS on **localhost:443** and forwards to OpenSearch
     :9200 (OpenSearch has security off, so the AWS signature is ignored)
  2. dummy `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` in the .env — without
     them `AWSV4SignerAuth()` raises before a socket is ever opened
  3. `REQUESTS_CA_BUNDLE` points at the shim's self-signed cert, which is how
     `verify_certs=True` is satisfied without editing the code

Proven on the laptop against the real code path (.env → load_dotenv →
unmodified `get_opensearch_client()`): `info()` returned 2.13.0 and a
`_count` query succeeded. Without the CA bundle it fails — that env var is
the load-bearing piece.

**Verify on the VM before indexing** (must print a version number):

    curl --cacert /etc/nginx/venue-os/cert.pem https://localhost/
    sudo systemctl restart search-api && sudo systemctl status search-api --no-pager

## STEP 5 — index the products (HOURS — start tonight, inside tmux)
The run takes 3-5 hours for 330k products and CANNOT resume — any restart
begins from zero (the code deletes the index first). So it MUST survive an
SSH drop / laptop sleep:

    tmux new -s pipeline
    cd /opt/pipeline
    sudo ./venv/bin/python scripts/pipeline.py 2>&1 | tee ~/pipeline.log
    # detach: press Ctrl-b, then d  → safe to close the laptop
    # reattach any time:  tmux attach -t pipeline

Watch progress from a second SSH window:

    curl -s localhost:9200/products/_count
    tail -f ~/pipeline.log

⚠️ While it runs: do NOT re-run setup-venue-azure.sh (it restarts OpenSearch
→ run dies). Portal deploy must happen BEFORE starting, or AFTER it finishes.
After it finishes (optional but good for the demo):

    sudo ./venv/bin/python scripts/backfill_images.py
    sudo ./venv/bin/python scripts/backfill_trending.py

Sanity check the DB metrics actually connected (must NOT be 0 rows error):

    docker exec venue-postgres psql -U postgres venue_ai -c "select count(*) from product_metrics;"

## STEP 5.5 — HTTPS (only AFTER DNS resolves to the new IP)
    nslookup venuemarketplace.xyz 8.8.8.8        # must show 20.219.141.225
    sudo certbot --nginx -d venuemarketplace.xyz -d www.venuemarketplace.xyz \
      -m pradeep.kumar@athinfosys.com --agree-tos -n
(certbot is already installed by the script; needs NSG port 80 open to ALL.
NOTE: a second 443 block already exists for the OpenSearch shim — it answers
only to the name `localhost`, so certbot's domain block coexists with it.
Until this runs there is NO https — test with http:// first.)

## STEP 6 — smoke test (10 minutes before the demo)
    curl https://venuemarketplace.xyz/                       → holding page / site
    https://venuemarketplace.xyz/docs                        → Swagger loads
    POST /search {"query":"red shoes"}                       → products
    GET  /autocomplete?q=sho                                 → suggestions
    POST /search/ai-assistant {"message":"gift under $50"}   → AI answer
    GET  /trending                                           → rows (after backfill)
    https://venuemarketplace.xyz/portal/                     → portal login → Overview

## Demo checklist
- [ ] Cloud team confirmed: NSG only 22/80/443 (22 from our IP, 80 to ALL),
      IP is Static, disk size known (`df -h`)
- [ ] DNS switched to 20.219.141.225 (site was already dead — zero risk)
- [ ] setup script ran clean (with PG_PW=shubham16)
- [ ] BOTH .env files filled + identical (grep check says 1 and 1)
- [ ] TLS shim answers (`curl --cacert ... https://localhost/`), search-api restarted
- [ ] portal files copied + portal .env filled + venue-portal running
- [ ] pipeline.py running in tmux (started tonight!) → finished (watch _count)
- [ ] certbot ran after DNS → https works
- [ ] /docs + one full search + AI assistant + portal login tested in browser
- [ ] (note) website root shows a holding page unless we get the real site
      build — demo the search via /docs + the shop widget + the portal

## Client portal — ALREADY BUILT (2026-08-24, tested on laptop with mock data)
Two NEW folders beside the backend (backend code untouched):
- `venue-portal-api/`        — read-only FastAPI on :8100 (Postgres + OpenSearch)
- `venue-client-dashboard/`  — React dashboard, built to `dist/` (base /portal/)

Pages: Overview (KPIs + growing chart + top searches), Live activity,
Trending, Products browser, blu AI assistant, blu login. Sign-in:
client id `venue` + PORTAL_PASSWORD from the portal .env.

To deploy — copy from the laptop to the VM, then re-run the setup script
(⚠️ NOT while pipeline.py is indexing — the script restarts containers):
    ssh venueDemo@20.219.141.225 "mkdir -p /tmp/portal-api"
    scp venue-portal-api/main.py venue-portal-api/requirements.txt \
        venueDemo@20.219.141.225:/tmp/portal-api/
    scp -r venue-client-dashboard/dist venueDemo@20.219.141.225:/tmp/portal-dist
    # on the VM  (note the /. — it copies CONTENTS, not a nested folder):
    sudo mkdir -p /opt/venue-portal/api /opt/venue-portal/dist
    sudo cp /tmp/portal-api/* /opt/venue-portal/api/
    sudo cp -r /tmp/portal-dist/. /opt/venue-portal/dist/
    sudo PG_PW=shubham16 bash setup-venue-azure.sh   # venv + service + nginx routes
    sudo nano /opt/venue-portal/api/.env   # fill OPENAI_API_KEY + PORTAL_PASSWORD
    sudo systemctl restart venue-portal
Portal URL: https://venuemarketplace.xyz/portal/
Trouble: portal login says "Too many attempts" → sudo systemctl restart venue-portal

## Phase 2 (AFTER the demo — not tomorrow)
Connect the venue portal into the bCloud ADMIN dashboard as a client card
(admin sees venue numbers beside the bCloud shops). Also: backups + a
down-alert before any real client relies on it.
