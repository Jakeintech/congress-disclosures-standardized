#!/usr/bin/env python3
"""Compute Trade-Bill-Lobbying Triple Correlation (STAR FEATURE).

This is the flagship feature that connects:
1. Member stock trades
2. Bills sponsored/cosponsored
3. Lobbying activity on those bills
4. Campaign contributions from lobbyists

Scoring:
- Member traded stock in company: 40 points
- Member sponsored/cosponsored bill: 30 points
- Company lobbied on that bill: 20 points
- Lobbyist contributed to member: 10 points
Total: 0-100 points
"""

import argparse
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any

import boto3
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

S3_BUCKET = os.environ.get("S3_BUCKET_NAME", "congress-disclosures-standardized")
S3_GOLD_PREFIX = os.environ.get("S3_GOLD_PREFIX", "gold")
S3_SILVER_PREFIX = os.environ.get("S3_SILVER_PREFIX", "silver")


def read_parquet_from_s3(s3_client: boto3.client, key: str) -> pd.DataFrame:
    """Read Parquet file from S3."""
    try:
        obj = s3_client.get_object(Bucket=S3_BUCKET, Key=key)
        df = pd.read_parquet(obj["Body"])
        logger.info(f"Read {len(df)} records from {key}")
        return df
    except Exception as e:
        logger.warning(f"Could not read {key}: {e}")
        return pd.DataFrame()


def load_ticker_client_mapping(s3_client: boto3.client) -> Dict[str, list]:
    """Create mapping from stock ticker to lobbying clients (companies).

    Uses industry classification and company name matching.
    Returns dict: {ticker: [client_names]}
    """
    # In production, this would use industry_classifier or explicit mappings
    # For now, return a simple mapping structure
    logger.info("Loading ticker-to-client mapping...")

    # Read clients
    clients_df = read_parquet_from_s3(
        s3_client,
        f"{S3_SILVER_PREFIX}/lobbying/clients/clients.parquet"
    )

    if clients_df.empty:
        return {}

    # Simple name-based matching (in production, use sophisticated matching)
    # Map common company names to tickers
    ticker_mapping = {}

    # Example mappings (would be much more extensive in production)
    company_to_ticker = {
        "APPLE": "AAPL",
        "MICROSOFT": "MSFT",
        "GOOGLE": "GOOGL",
        "ALPHABET": "GOOGL",
        "AMAZON": "AMZN",
        "META": "META",
        "FACEBOOK": "META",
        "NVIDIA": "NVDA",
        "TESLA": "TSLA",
        "BOEING": "BA",
        "LOCKHEED MARTIN": "LMT",
        "RAYTHEON": "RTX",
        "PFIZER": "PFE",
        "MODERNA": "MRNA",
        "JOHNSON & JOHNSON": "JNJ",
        "JPMORGAN": "JPM",
        "GOLDMAN SACHS": "GS",
        "BANK OF AMERICA": "BAC",
    }

    for _, client in clients_df.iterrows():
        client_name = str(client["name"]).upper()

        for company, ticker in company_to_ticker.items():
            if company in client_name:
                if ticker not in ticker_mapping:
                    ticker_mapping[ticker] = []
                ticker_mapping[ticker].append(client["name"])

    logger.info(f"Mapped {len(ticker_mapping)} tickers to lobbying clients")
    return ticker_mapping


def generate_explanation(row: pd.Series) -> str:
    """Generate human-readable explanation of the correlation."""
    parts = []

    # Member and trade
    member = row.get("member_name", row.get("member_bioguide_id", "Unknown"))
    ticker = row.get("ticker", "Unknown")
    trade_type = row.get("trade_type", "traded")
    trade_amount = row.get("trade_amount_display", "Unknown")
    trade_date = row.get("trade_date", "")

    parts.append(
        f"{member} {trade_type.lower()} ${trade_amount} of {ticker} stock on {trade_date}"
    )

    # Bill role
    if row.get("member_role"):
        bill_id = row.get("bill_id", "")
        bill_title = row.get("bill_title", "")
        parts.append(
            f"{row['member_role']} {bill_id} ({bill_title[:80]}...)"
        )

    # Lobbying
    if row.get("client_name"):
        lobbying_spend = row.get("lobbying_spend", 0)
        client = row.get("client_name")
        registrant = row.get("registrant_name", "")
        parts.append(
            f"{client} paid ${lobbying_spend:,.0f} to {registrant} to lobby on this bill"
        )

    # Contributions
    if row.get("contribution_amount", 0) > 0:
        contribution = row.get("contribution_amount", 0)
        parts.append(
            f"Lobbyists contributed ${contribution:,.2f} to {member}'s campaign"
        )

    # Timing
    if row.get("days_trade_to_bill_action"):
        days = row["days_trade_to_bill_action"]
        if days > 0:
            parts.append(f"{abs(days)} days after bill action")
        else:
            parts.append(f"{abs(days)} days before bill action")

    return ". ".join(parts) + "."


def compute_triple_correlation(s3_client: boto3.client, year: int, congress: int) -> pd.DataFrame:
    """Compute the triple correlation between trades, bills, and lobbying."""

    logger.info("Loading required datasets...")

    # Load member trades (PTR transactions)
    trades_df = read_parquet_from_s3(
        s3_client,
        f"{S3_GOLD_PREFIX}/house/financial/facts/fact_ptr_transactions/fact_ptr_transactions.parquet"
    )

    # Filter to year
    if not trades_df.empty:
        trades_df["transaction_date"] = pd.to_datetime(trades_df["transaction_date"])
        trades_df = trades_df[
            (trades_df["transaction_date"].dt.year >= year - 1) &
            (trades_df["transaction_date"].dt.year <= year + 1)
        ]

    # Load member-bill roles
    member_bill_df = read_parquet_from_s3(
        s3_client,
        f"{S3_GOLD_PREFIX}/congress/fact_member_bill_role/fact_member_bill_role.parquet"
    )

    if not member_bill_df.empty:
        member_bill_df = member_bill_df[member_bill_df["congress"] == congress]

    # Load bill-lobbying correlations
    bill_lobbying_df = read_parquet_from_s3(
        s3_client,
        f"{S3_GOLD_PREFIX}/lobbying/agg_bill_lobbying_activity/year={year}/agg_bill_lobbying_activity.parquet"
    )

    # Load bill actions (for timing)
    bill_actions_df = read_parquet_from_s3(
        s3_client,
        f"{S3_GOLD_PREFIX}/congress/agg_bill_latest_action/agg_bill_latest_action.parquet"
    )

    # Load contributions
    contributions_df = read_parquet_from_s3(
        s3_client,
        f"{S3_SILVER_PREFIX}/lobbying/contributions/year={year}/contributions.parquet"
    )

    if trades_df.empty or member_bill_df.empty or bill_lobbying_df.empty:
        logger.error("Required datasets not available")
        return pd.DataFrame()

    # Load ticker-client mapping
    ticker_client_map = load_ticker_client_mapping(s3_client)

    logger.info("Computing correlations...")
    correlations = []

    # For each member trade
    for _, trade in trades_df.iterrows():
        member_id = trade["member_bioguide_id"]
        ticker = trade.get("ticker", "")
        trade_date = trade["transaction_date"]

        if not ticker or ticker not in ticker_client_map:
            continue

        # Find bills this member sponsored/cosponsored
        member_bills = member_bill_df[member_bill_df["member_bioguide_id"] == member_id]

        for _, bill_role in member_bills.iterrows():
            bill_id = bill_role["bill_id"]

            # Check if this bill was lobbied
            bill_lobby = bill_lobbying_df[bill_lobbying_df["bill_id"] == bill_id]

            if bill_lobby.empty:
                continue

            # Check if any of the lobbying clients match the traded ticker
            for _, lobby in bill_lobby.iterrows():
                client_names = lobby.get("client_names", [])

                # Check if any client matches the ticker
                ticker_clients = ticker_client_map[ticker]
                matching_clients = [c for c in client_names if c in ticker_clients]

                if not matching_clients:
                    continue

                # We have a correlation! Calculate score
                score = 0

                # 1. Member traded ticker (40 points)
                score += 40

                # 2. Member sponsored/cosponsored bill (30 points)
                score += 30

                # 3. Company lobbied on bill (20 points)
                score += 20

                # 4. Check for contributions (10 points)
                contribution_amount = 0
                contribution_dates = []

                if not contributions_df.empty:
                    # Match contributions to member (by name, simplified)
                    # In production, use proper member name lookup
                    member_contributions = contributions_df[
                        contributions_df["honoree_name"].str.contains(
                            str(trade.get("member_name", "")),
                            case=False,
                            na=False
                        )
                    ]

                    if not member_contributions.empty:
                        contribution_amount = member_contributions["amount"].sum()
                        contribution_dates = member_contributions["date"].tolist()
                        score += 10

                # Calculate timing
                days_trade_to_bill_action = None
                bill_action_date = None

                if not bill_actions_df.empty:
                    bill_action = bill_actions_df[bill_actions_df["bill_id"] == bill_id]
                    if not bill_action.empty:
                        bill_action_date = pd.to_datetime(bill_action.iloc[0]["latest_action_date"])
                        days_trade_to_bill_action = (trade_date - bill_action_date).days

                # Create correlation record
                correlation = {
                    "member_bioguide_id": member_id,
                    "member_name": trade.get("member_name", ""),
                    "bill_id": bill_id,
                    "bill_title": bill_role.get("bill_title", ""),
                    "ticker": ticker,
                    "company_name": matching_clients[0],
                    "trade_date": trade_date.date().isoformat(),
                    "trade_type": trade.get("transaction_type", ""),
                    "trade_amount_display": trade.get("amount_display", ""),
                    "member_role": bill_role.get("role_type", ""),
                    "bill_action_date": bill_action_date.date().isoformat() if bill_action_date else None,
                    "client_name": matching_clients[0],
                    "registrant_name": lobby.get("registrant_names", [""])[0] if lobby.get("registrant_names") else "",
                    "lobbying_spend": lobby.get("total_lobbying_spend", 0),
                    "lobbying_dates": lobby.get("filing_quarters", []),
                    "contribution_amount": contribution_amount,
                    "contribution_dates": contribution_dates,
                    "correlation_score": score,
                    "days_trade_to_bill_action": days_trade_to_bill_action,
                }

                # Generate explanation
                correlation["explanation_text"] = generate_explanation(pd.Series(correlation))

                correlations.append(correlation)

    correlations_df = pd.DataFrame(correlations)

    if correlations_df.empty:
        logger.warning("No triple correlations found")
        return pd.DataFrame()

    # Add metadata
    correlations_df["year"] = year
    correlations_df["congress"] = congress
    correlations_df["dt_computed"] = datetime.utcnow().isoformat()

    # Sort by correlation score
    correlations_df = correlations_df.sort_values("correlation_score", ascending=False)

    logger.info(f"Found {len(correlations_df)} triple correlations")
    return correlations_df


def write_gold_table(df: pd.DataFrame, year: int) -> None:
    """Write DataFrame to Gold Parquet table."""
    if df.empty:
        logger.warning("No data to write")
        return

    s3_key = f"{S3_GOLD_PREFIX}/lobbying/agg_trade_bill_lobbying_correlation/year={year}/agg_triple_correlation.parquet"
    logger.info(f"Writing Gold table to s3://{S3_BUCKET}/{s3_key}")

    table = pa.Table.from_pandas(df)

    with pa.BufferOutputStream() as out_stream:
        pq.write_table(table, out_stream, compression="snappy")
        buffer = out_stream.getvalue()

        s3_client = boto3.client("s3")
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=buffer.to_pybytes(),
            ContentType="application/x-parquet",
        )

    logger.info(f"Wrote {len(df)} triple correlations to {s3_key}")


def main():
    parser = argparse.ArgumentParser(description="Compute Trade-Bill-Lobbying triple correlation")
    parser.add_argument("--year", type=int, required=True, help="Filing year")
    parser.add_argument("--congress", type=int, required=True, help="Congress number")
    args = parser.parse_args()

    logger.info(f"Computing triple correlation for year {args.year}, Congress {args.congress}")

    s3_client = boto3.client("s3")
    df = compute_triple_correlation(s3_client, args.year, args.congress)

    if df.empty:
        logger.warning("No triple correlations computed")
        sys.exit(0)

    write_gold_table(df, args.year)

    # Print summary
    logger.info(f"\n{'='*60}")
    logger.info("TRIPLE CORRELATION SUMMARY (STAR FEATURE)")
    logger.info(f"{'='*60}")
    logger.info(f"Total correlations: {len(df)}")
    logger.info(f"Perfect scores (100): {(df['correlation_score'] == 100).sum()}")
    logger.info(f"High scores (>=80): {(df['correlation_score'] >= 80).sum()}")
    logger.info(f"Average score: {df['correlation_score'].mean():.1f}")
    logger.info(f"\nTop 10 correlations:")
    top_correlations = df.head(10)[[
        "member_name", "ticker", "bill_id", "correlation_score"
    ]]
    for _, row in top_correlations.iterrows():
        logger.info(
            f"  {row['member_name']} | {row['ticker']} | {row['bill_id']} | Score: {row['correlation_score']}"
        )

    logger.info(f"\nTop correlation explanation:")
    if not df.empty:
        logger.info(df.iloc[0]["explanation_text"])


if __name__ == "__main__":
    main()
