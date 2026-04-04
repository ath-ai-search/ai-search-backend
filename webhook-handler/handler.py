"""
webhook-handler/handler.py
============================
Receives BigCommerce webhook → sends message to SQS queue.
Terraform auto-packages this file — no manual zip needed.
"""

import json
import logging
import os

import boto3

logger    = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))

sqs       = boto3.client("sqs")
QUEUE_URL = os.environ["SQS_QUEUE_URL"]


def lambda_handler(event, context):
    try:
        body       = json.loads(event.get("body", "{}"))
        product_id = body.get("data", {}).get("id")
        scope      = body.get("scope", "")

        logger.info(f"Webhook received — scope={scope} product_id={product_id}")

        if not product_id:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "No product_id in webhook payload"})
            }

        sqs.send_message(
            QueueUrl=QUEUE_URL,
            MessageBody=json.dumps({
                "product_id": product_id,
                "scope":      scope,
            })
        )

        logger.info(f"Queued product_id={product_id} scope={scope}")

        return {
            "statusCode": 200,
            "body": json.dumps({"status": "queued", "product_id": product_id})
        }

    except Exception as e:
        logger.error(f"Webhook handler error: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
