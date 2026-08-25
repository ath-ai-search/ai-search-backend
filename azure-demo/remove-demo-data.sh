#!/bin/bash
# 🧹 Removes EVERY sample row loaded by seed-demo-data.sh (tag: demo-%).
# Real tracked events are never touched.
set -e
docker exec -i venue-postgres psql -U postgres -d venue_ai -c \
  "DELETE FROM events WHERE session_id LIKE 'demo-%';"
echo "=== sample data removed — dashboards show only real tracking again ==="
