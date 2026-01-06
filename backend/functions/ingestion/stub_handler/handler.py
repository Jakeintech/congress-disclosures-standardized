"""
Generic Stub Handler
Returns success for any input. Used as a placeholder for pending pipeline steps.
"""
import logging
import os

logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

def lambda_handler(event, context):
    logger.info(f"Stub handler invoked with event: {event}")
    return {
        "status": "success",
        "message": "Step completed via stub handler",
        "input": event
    }
