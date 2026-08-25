#!/bin/bash
# =====================================================================
# 🩺 HEAL THE RESTORED venue_ai SCHEMA — pure DDL, ZERO code changes.
#
# The April backup predates the current backend code: the models in
# api/app/routers/tracking.py expect columns the dumped tables do not
# have (events.visitor_id, product_metrics.visitor_id/trending_score/
# variant_image/last_seen + the uq_visitor_product constraint that
# ON CONFLICT needs, orders.visitor_id). Every /track insert therefore
# fails inside the background task (the API still answers 200) — which
# is why NO shopper event has landed since the restore.
#
# Run:  sudo bash /opt/pipeline/azure-demo/fix-tracking-schema.sh
# Idempotent — safe to run any number of times.
# =====================================================================
set -e

docker exec -i venue-postgres psql -U postgres -d venue_ai <<'SQL'
-- ---- events: the tracker writes visitor_id; dump has user_id varchar(50)
ALTER TABLE events ADD COLUMN IF NOT EXISTS visitor_id varchar(100);
CREATE INDEX IF NOT EXISTS ix_events_visitor_id ON events (visitor_id);
ALTER TABLE events ALTER COLUMN user_id TYPE varchar(100);

-- ---- product_metrics: per-visitor rows + trending machinery
ALTER TABLE product_metrics ADD COLUMN IF NOT EXISTS visitor_id varchar(100);
ALTER TABLE product_metrics ADD COLUMN IF NOT EXISTS trending_score numeric DEFAULT 0;
ALTER TABLE product_metrics ADD COLUMN IF NOT EXISTS variant_image text;
ALTER TABLE product_metrics ADD COLUMN IF NOT EXISTS last_seen timestamp DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE product_metrics ADD COLUMN IF NOT EXISTS created_at timestamp DEFAULT CURRENT_TIMESTAMP;

-- old aggregate rows get a synthetic visitor so the new unique pair holds
UPDATE product_metrics SET visitor_id = 'legacy-' || id::text WHERE visitor_id IS NULL;

-- score the legacy rows with the exact formula the code uses
UPDATE product_metrics
   SET trending_score = 1.0 + (COALESCE(views,0) * 1) + (COALESCE(clicks,0) * 2)
                            + (COALESCE(wishlist,0) * 3) + (COALESCE(carts,0) * 5)
                            + (COALESCE(purchases,0) * 10)
 WHERE COALESCE(trending_score, 0) = 0;

-- the upsert's ON CONFLICT target
DO $$ BEGIN
  ALTER TABLE product_metrics ADD CONSTRAINT uq_visitor_product UNIQUE (visitor_id, product_id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;

-- ---- orders: purchase events create orders with visitor_id
ALTER TABLE orders ADD COLUMN IF NOT EXISTS visitor_id varchar(100);
ALTER TABLE orders ALTER COLUMN user_id TYPE varchar(100);

-- proof
SELECT 'events cols'          AS what, COUNT(*) FROM information_schema.columns WHERE table_name='events'          AND column_name='visitor_id'
UNION ALL
SELECT 'metrics cols',        COUNT(*) FROM information_schema.columns WHERE table_name='product_metrics' AND column_name='trending_score'
UNION ALL
SELECT 'uq constraint',       COUNT(*) FROM pg_constraint WHERE conname='uq_visitor_product'
UNION ALL
SELECT 'orders cols',         COUNT(*) FROM information_schema.columns WHERE table_name='orders'          AND column_name='visitor_id';
SQL

echo ""
echo "=== schema healed — sending a live test event through the public /track ==="
curl -s -X POST https://venuemarketplace.xyz/track -H "Content-Type: application/json" \
  -d '{"events":[{"event_type":"view","session_id":"schema-check","product_id":"schema-check-product"}]}'
echo ""
sleep 3
docker exec -i venue-postgres psql -U postgres -d venue_ai -t -c \
  "SELECT 'LANDED: ' || COUNT(*) FROM events WHERE session_id = 'schema-check';"
docker exec -i venue-postgres psql -U postgres -d venue_ai -c \
  "DELETE FROM events WHERE session_id = 'schema-check';
   DELETE FROM product_metrics WHERE product_id = 'schema-check-product';"
echo "=== DONE — if LANDED: 1 above, real shopper tracking is ALIVE ==="
