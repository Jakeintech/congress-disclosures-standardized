"""
Lambda: Transaction Alert Handler

Triggered by: EventBridge rule when new transactions added to Gold layer
Purpose: Generate and publish alerts for filtered transactions

Alert Criteria (factual, data-driven):
- Amount >= $50,000
- Cryptocurrency transactions (any amount)
- Committee correlation score >= 0.7
- Within 7 days of recent activity
"""

import json
import boto3
import os
from datetime import datetime
from typing import Dict, Any, List

sns = boto3.client('sns')
dynamodb = boto3.resource('dynamodb')

SNS_TOPIC_ARN = os.environ.get('ALERT_SNS_TOPIC_ARN')
ALERTS_TABLE_NAME = os.environ.get('ALERTS_TABLE_NAME', 'congress-disclosures-alerts')

alerts_table = dynamodb.Table(ALERTS_TABLE_NAME)

# Alert thresholds
AMOUNT_THRESHOLD = 50000  # $50K
COMMITTEE_CORRELATION_THRESHOLD = 0.7
CRYPTO_KEYWORDS = ['bitcoin', 'btc', 'ethereum', 'eth', 'crypto', 'coinbase']


def meets_alert_criteria(transaction: Dict[str, Any]) -> bool:
    """
    Determine if transaction meets alert criteria.

    Factual criteria:
    1. High-value: amount >= $50,000
    2. Crypto exposure: asset name contains crypto keywords
    3. High committee correlation: score >= 0.7
    4. Recent activity: within 7 days
    """

    # Criterion 1: High-value transactions
    if transaction.get('amount_low', 0) >= AMOUNT_THRESHOLD:
        return True

    # Criterion 2: Cryptocurrency transactions
    asset_name = transaction.get('asset_name', '').lower()
    if any(keyword in asset_name for keyword in CRYPTO_KEYWORDS):
        return True

    # Criterion 3: High committee correlation
    if transaction.get('committee_correlation_score', 0) >= COMMITTEE_CORRELATION_THRESHOLD:
        return True

    # Criterion 4: Recent high-correlation activity
    if transaction.get('is_within_7d', False) and transaction.get('committee_correlation_score', 0) >= 0.5:
        return True

    return False


def generate_alert_message(transaction: Dict[str, Any]) -> str:
    """
    Generate factual alert message.

    Format: "[TRANSACTION] Member: Action Amount in Asset [Committee Context]"
    """

    member_name = transaction.get('member_name') or transaction.get('full_name', 'Unknown Member')
    party = transaction.get('party', 'Unknown')
    state = transaction.get('state', 'Unknown')
    trans_type = transaction.get('transaction_type', 'transaction')
    asset_name = transaction.get('asset_name', 'Unknown Asset')
    ticker = transaction.get('ticker')
    amount_low = transaction.get('amount_low', 0)
    amount_high = transaction.get('amount_high')
    committee = transaction.get('committee_name')
    correlation_score = transaction.get('committee_correlation_score', 0)

    # Format amount
    if amount_high and amount_high > amount_low:
        amount_str = f"${amount_low:,}-${amount_high:,}"
    else:
        amount_str = f"${amount_low:,}+"

    # Base message
    message = f"[TRANSACTION] {member_name} ({party}-{state}): {trans_type} {amount_str} in {asset_name}"

    # Add ticker if available
    if ticker:
        message += f" (${ticker})"

    # Add committee context if correlation exists
    if committee and correlation_score >= 0.5:
        message += f" | Committee: {committee} (correlation: {correlation_score:.2f})"

    return message


def publish_alert(alert_message: str, transaction: Dict[str, Any]):
    """Publish alert to SNS topic."""

    if not SNS_TOPIC_ARN:
        print("WARNING: SNS_TOPIC_ARN not configured, skipping publish")
        return

    message_data = {
        'alert_message': alert_message,
        'transaction': transaction,
        'timestamp': datetime.utcnow().isoformat(),
        'alert_type': 'transaction_alert'
    }

    try:
        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Message=json.dumps(message_data),
            Subject='Congressional Transaction Alert',
            MessageAttributes={
                'alert_type': {'DataType': 'String', 'StringValue': 'transaction_alert'},
                'member_id': {'DataType': 'String', 'StringValue': transaction.get('bioguide_id', 'unknown')}
            }
        )
        print(f"✓ Published alert to SNS: {alert_message}")
    except Exception as e:
        print(f"ERROR publishing to SNS: {e}")
        raise


def store_alert(alert_id: str, alert_message: str, transaction: Dict[str, Any]):
    """Store alert in DynamoDB for tracking and deduplication."""

    try:
        alerts_table.put_item(
            Item={
                'alert_id': alert_id,
                'alert_message': alert_message,
                'alert_type': 'transaction_alert',
                'bioguide_id': transaction.get('bioguide_id'),
                'transaction_date': transaction.get('transaction_date'),
                'asset_name': transaction.get('asset_name'),
                'ticker': transaction.get('ticker'),
                'amount_low': transaction.get('amount_low'),
                'committee_correlation_score': transaction.get('committee_correlation_score', 0),
                'created_at': datetime.utcnow().isoformat(),
                'ttl': int(datetime.utcnow().timestamp()) + (90 * 24 * 60 * 60)  # 90 days
            }
        )
        print(f"✓ Stored alert in DynamoDB: {alert_id}")
    except Exception as e:
        print(f"ERROR storing alert in DynamoDB: {e}")
        raise


def check_alert_exists(alert_id: str) -> bool:
    """Check if alert already exists to prevent duplicates."""

    try:
        response = alerts_table.get_item(Key={'alert_id': alert_id})
        return 'Item' in response
    except Exception as e:
        print(f"ERROR checking existing alert: {e}")
        return False


def lambda_handler(event, context):
    """
    Lambda handler for transaction alerts.

    Event format:
    {
        "transactions": [
            {
                "bioguide_id": "D000032",
                "member_name": "Byron Donalds",
                "full_name": "Byron Donalds",
                "party": "R",
                "state": "FL",
                "transaction_date": "2025-01-05",
                "asset_name": "Bitcoin",
                "ticker": "BTC",
                "transaction_type": "Purchase",
                "amount_low": 100000,
                "amount_high": 250000,
                "committee_name": "House Subcommittee on Digital Assets",
                "committee_correlation_score": 1.0,
                "is_within_7d": true
            }
        ]
    }

    Returns:
    {
        "statusCode": 200,
        "body": {
            "alerts_generated": 2,
            "transactions_processed": 10
        }
    }
    """

    print(f"Received event: {json.dumps(event)}")

    transactions = event.get('transactions', [])
    alerts_generated = 0
    alerts_skipped = 0

    print(f"Processing {len(transactions)} transactions...")

    for transaction in transactions:
        # Check if transaction meets alert criteria
        if not meets_alert_criteria(transaction):
            continue

        # Generate unique alert ID
        bioguide = transaction.get('bioguide_id', 'unknown')
        trans_date = transaction.get('transaction_date', 'unknown')
        ticker = transaction.get('ticker', 'NOTICKER')
        alert_id = f"{bioguide}_{trans_date}_{ticker}"

        # Check if alert already exists
        if check_alert_exists(alert_id):
            print(f"Alert {alert_id} already exists, skipping")
            alerts_skipped += 1
            continue

        # Generate alert message
        alert_message = generate_alert_message(transaction)

        # Publish and store
        try:
            publish_alert(alert_message, transaction)
            store_alert(alert_id, alert_message, transaction)
            alerts_generated += 1
        except Exception as e:
            print(f"ERROR processing alert {alert_id}: {e}")
            continue

    print(f"✓ Generated {alerts_generated} new alerts ({alerts_skipped} duplicates skipped)")

    return {
        'statusCode': 200,
        'body': json.dumps({
            'alerts_generated': alerts_generated,
            'alerts_skipped': alerts_skipped,
            'transactions_processed': len(transactions)
        })
    }
