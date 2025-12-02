"""Deprecated Textract-based structured extraction handler.

This Lambda previously orchestrated AWS Textract document analysis. Textract
support has been removed from the pipeline to eliminate the dependency and
cost. The handler now returns a 410 status to signal callers to migrate to the
code-based extraction workflow.
"""

import json
import logging
import os
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

RETIREMENT_MESSAGE = (
    "Textract-based structured extraction is removed. Use the code-based "
    "extraction workflow instead."
)


def handler(event, context):
    """Return a clear message indicating the endpoint has been retired."""
    logger.info("Structured Textract handler invoked; returning retirement notice.")
    return {
        "statusCode": 410,
        "body": json.dumps(
            {
                "message": RETIREMENT_MESSAGE,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
        ),
    }
