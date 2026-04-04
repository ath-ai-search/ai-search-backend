"""
scripts/register_webhooks.py
==============================
Automatically registers BigCommerce webhooks pointing
to your API Gateway URL after terraform apply.

PROCESS:
  Step 1 → terraform apply  (deploys everything)
  Step 2 → terraform output webhook_url  (get the URL)
  Step 3 → python scripts/register_webhooks.py  (run this script)
  Step 4 → Done! BigCommerce now fires webhooks automatically

Run:
    pip install requests
    python scripts/register_webhooks.py
"""

import json
import requests

import os
from dotenv import load_dotenv

# Load variables from the .env file
load_dotenv()

# ============================================================
# ✏️ VALUES LOADED FROM .ENV
# ============================================================

CONFIG = {
    # Loaded from your .env file
    "WEBHOOK_DESTINATION_URL": os.getenv("WEBHOOK_DESTINATION_URL"),

    # Your BigCommerce credentials loaded from .env
    "BIGCOMMERCE_STORE_HASH":   os.getenv("BIGCOMMERCE_STORE_HASH"),
    "BIGCOMMERCE_ACCESS_TOKEN": os.getenv("BIGCOMMERCE_ACCESS_TOKEN"),
    "BIGCOMMERCE_CLIENT_ID":    os.getenv("BIGCOMMERCE_CLIENT_ID"),
}
# ============================================================
# WEBHOOKS TO REGISTER
# These cover: create, update, delete, inventory changes
# ============================================================

WEBHOOK_SCOPES = [
    "store/product/created",
    "store/product/updated",
    "store/product/deleted",
    "store/product/inventory/updated",
    "store/product/inventory/order/updated",
]

# ============================================================


def get_existing_webhooks(store_hash: str, access_token: str) -> list:
    """Fetch all existing webhooks from BigCommerce."""
    url = f"https://api.bigcommerce.com/stores/{store_hash}/v3/hooks"
    headers = {
        "X-Auth-Token": access_token,
        "Accept":       "application/json",
    }
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json().get("data", [])


def delete_webhook(store_hash: str, access_token: str, hook_id: int):
    """Delete an existing webhook."""
    url = f"https://api.bigcommerce.com/stores/{store_hash}/v3/hooks/{hook_id}"
    headers = {"X-Auth-Token": access_token}
    resp = requests.delete(url, headers=headers)
    resp.raise_for_status()
    print(f"  🗑  Deleted old webhook id={hook_id}")


def register_webhook(
    store_hash: str,
    access_token: str,
    client_id: str,
    scope: str,
    destination: str,
) -> dict:
    """Register a single webhook in BigCommerce."""
    url = f"https://api.bigcommerce.com/stores/{store_hash}/v3/hooks"
    headers = {
        "X-Auth-Token": access_token,
        "Content-Type": "application/json",
        "Accept":       "application/json",
    }
    payload = {
        "scope":       scope,
        "destination": destination,
        "is_active":   True,
        "headers":     {},
    }
    resp = requests.post(url, headers=headers, json=payload)
    resp.raise_for_status()
    return resp.json().get("data", {})


def main():
    store_hash   = CONFIG["BIGCOMMERCE_STORE_HASH"]
    access_token = CONFIG["BIGCOMMERCE_ACCESS_TOKEN"]
    client_id    = CONFIG["BIGCOMMERCE_CLIENT_ID"]
    destination  = CONFIG["WEBHOOK_DESTINATION_URL"]

    print("\n" + "=" * 55)
    print("  BigCommerce Webhook Registration")
    print("=" * 55)
    print(f"  Store:       {store_hash}")
    print(f"  Destination: {destination}")
    print("=" * 55 + "\n")

    # Step 1 — fetch existing webhooks
    print("📋 Fetching existing webhooks...")
    existing = get_existing_webhooks(store_hash, access_token)
    print(f"   Found {len(existing)} existing webhooks\n")

    # Step 2 — delete old webhooks pointing to same destination
    # (avoids duplicate registrations on re-run)
    for hook in existing:
        if hook.get("destination") == destination:
            delete_webhook(store_hash, access_token, hook["id"])

    # Step 3 — register all scopes
    print("🔗 Registering webhooks...")
    registered = []
    failed     = []

    for scope in WEBHOOK_SCOPES:
        try:
            hook = register_webhook(
                store_hash, access_token, client_id, scope, destination
            )
            registered.append(hook)
            print(f"  ✅  {scope}")
            print(f"      id={hook.get('id')}  active={hook.get('is_active')}")
        except Exception as e:
            failed.append(scope)
            print(f"  ❌  {scope} — ERROR: {e}")

    # Step 4 — summary
    print("\n" + "=" * 55)
    print(f"  ✅ Registered: {len(registered)}/{len(WEBHOOK_SCOPES)}")
    if failed:
        print(f"  ❌ Failed:     {len(failed)}")
        for f in failed:
            print(f"     - {f}")
    print("=" * 55)

    if registered:
        print("\n🎉 Webhooks are now active!")
        print("   BigCommerce will automatically fire webhooks to:")
        print(f"   {destination}")
        print("\n   Flow:")
        print("   BigCommerce → API Gateway → Lambda → SQS → OpenSearch")
    print()


if __name__ == "__main__":
    main()
