#!/bin/bash
# =====================================================================
# 🎬 DEMO SAMPLE DATA — loads ~1,500 realistic shopper events into the
# venue_ai events table so the dashboards show a month at real scale:
# ~500 searches, ~260 product clicks, ~120 carts, ~88 purchases worth
# ≈ $30,000, spread over the last 14 days (heavier on recent days).
#
# EVERY row is tagged  session_id = 'demo-…'  →  remove them ALL with:
#   sudo bash /opt/pipeline/azure-demo/remove-demo-data.sh
#
# ⚠️ In the meeting, present this view as "sample data loaded to show
# the dashboard at scale". Run the remove script after the meeting so
# real tracking stays clean.
#
# Run:  sudo bash /opt/pipeline/azure-demo/seed-demo-data.sh
# Idempotent: clears old demo rows first, then loads a fresh set.
# =====================================================================
set -e

docker exec -i venue-postgres psql -U postgres -d venue_ai <<'SQL'
DELETE FROM events WHERE session_id LIKE 'demo-%';

-- real product slugs from the store's own history, reused for realism
WITH ids AS (
  SELECT array_agg(product_id) AS a FROM (
    SELECT DISTINCT product_id FROM events
    WHERE product_id IS NOT NULL AND product_id <> '' LIMIT 300) s
),
qs AS (
  SELECT ARRAY[
    'running shoes for men','summer dress','bluetooth speaker','laptop bag',
    'wireless earbuds','office chair','gold watch','denim jacket',
    'yoga mat','kitchen knife set','table lamp','sneakers for women',
    'leather wallet','gaming mouse','winter coat','smart watch',
    'camping tent','baby stroller','coffee maker','hiking boots',
    'evening gown','phone case','sunglasses','backpack for school',
    'air fryer','wedding shoes','formal shirt men','curtains for bedroom',
    'water bottle','makeup kit'] AS a
)

-- searches (~500) — what shoppers typed
INSERT INTO events (id, event_type, session_id, query, "position", value, source, created_at)
SELECT nextval('events_id_seq'), 'search', 'demo-s' || (g % 160),
       qs.a[1 + floor(random() * cardinality(qs.a))::int],
       (5 + floor(random() * 300))::int,
       (120 + random() * 900)::real,
       'search',
       now() - (power(random(), 1.6) * interval '14 days')
FROM generate_series(1, 500) g, qs;

-- product views (~520)
WITH ids AS (SELECT array_agg(product_id) AS a FROM (
  SELECT DISTINCT product_id FROM events
  WHERE product_id IS NOT NULL AND product_id <> '' AND session_id NOT LIKE 'demo-%' LIMIT 300) s)
INSERT INTO events (id, event_type, session_id, product_id, created_at)
SELECT nextval('events_id_seq'), 'view', 'demo-s' || (g % 160),
       ids.a[1 + floor(random() * cardinality(ids.a))::int],
       now() - (power(random(), 1.6) * interval '14 days')
FROM generate_series(1, 520) g, ids;

-- clicks from results (~260)
WITH ids AS (SELECT array_agg(product_id) AS a FROM (
  SELECT DISTINCT product_id FROM events
  WHERE product_id IS NOT NULL AND product_id <> '' AND session_id NOT LIKE 'demo-%' LIMIT 300) s)
INSERT INTO events (id, event_type, session_id, product_id, created_at)
SELECT nextval('events_id_seq'), 'click', 'demo-s' || (g % 160),
       ids.a[1 + floor(random() * cardinality(ids.a))::int],
       now() - (power(random(), 1.6) * interval '14 days')
FROM generate_series(1, 260) g, ids;

-- add to cart (~120) + wishlist (~60)
WITH ids AS (SELECT array_agg(product_id) AS a FROM (
  SELECT DISTINCT product_id FROM events
  WHERE product_id IS NOT NULL AND product_id <> '' AND session_id NOT LIKE 'demo-%' LIMIT 300) s)
INSERT INTO events (id, event_type, session_id, product_id, created_at)
SELECT nextval('events_id_seq'),
       CASE WHEN g <= 120 THEN 'add_to_cart' ELSE 'wishlist' END,
       'demo-s' || (g % 160),
       ids.a[1 + floor(random() * cardinality(ids.a))::int],
       now() - (power(random(), 1.6) * interval '14 days')
FROM generate_series(1, 180) g, ids;

-- purchases (~88, values 150–600 → ≈ $30k total revenue)
WITH ids AS (SELECT array_agg(product_id) AS a FROM (
  SELECT DISTINCT product_id FROM events
  WHERE product_id IS NOT NULL AND product_id <> '' AND session_id NOT LIKE 'demo-%' LIMIT 300) s)
INSERT INTO events (id, event_type, session_id, product_id, value, created_at)
SELECT nextval('events_id_seq'), 'purchase', 'demo-s' || (g % 160),
       ids.a[1 + floor(random() * cardinality(ids.a))::int],
       (150 + random() * 450)::real,
       now() - (power(random(), 1.6) * interval '14 days')
FROM generate_series(1, 88) g, ids;

-- what did we load?
SELECT event_type, COUNT(*), COALESCE(ROUND(SUM(value)::numeric), 0) AS total_value
FROM events WHERE session_id LIKE 'demo-%'
GROUP BY event_type ORDER BY event_type;
SQL

echo ""
echo "=== DONE — sample data loaded. Dashboards show scale now. ==="
echo "=== After the meeting:  sudo bash /opt/pipeline/azure-demo/remove-demo-data.sh ==="
