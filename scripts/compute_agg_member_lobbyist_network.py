#!/usr/bin/env python3
"""Compute member-lobbyist network aggregate.

Creates connection graph between members and lobbyists based on:
- Bills sponsored/cosponsored that were lobbied
- Committee overlap with lobbying activity
- Political contributions received
- Industry/issue overlap
"""

import argparse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

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
S3_SILVER_PREFIX = os.environ.get("S3_SILVER_PREFIX", "silver")
S3_GOLD_PREFIX = os.environ.get("S3_GOLD_PREFIX", "gold")


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


def compute_network(s3_client: boto3.client, year: int, congress: int) -> pd.DataFrame:
    """Compute member-lobbyist network connections."""

    # Read necessary tables
    logger.info("Reading data tables...")

    # Bill-lobbying correlations
    bill_lobbying_df = read_parquet_from_s3(
        s3_client,
        f"{S3_GOLD_PREFIX}/lobbying/agg_bill_lobbying_activity/year={year}/agg_bill_lobbying_activity.parquet"
    )

    # Member-bill roles (sponsors/cosponsors)
    member_bill_df = read_parquet_from_s3(
        s3_client,
        f"{S3_GOLD_PREFIX}/congress/fact_member_bill_role/fact_member_bill_role.parquet"
    )

    # Lobbying contributions
    contributions_df = read_parquet_from_s3(
        s3_client,
        f"{S3_SILVER_PREFIX}/lobbying/contributions/year={year}/contributions.parquet"
    )

    # Lobbyists
    lobbyists_df = read_parquet_from_s3(
        s3_client,
        f"{S3_SILVER_PREFIX}/lobbying/lobbyists/year={year}/lobbyists.parquet"
    )

    # Fact lobbying activity
    fact_lobbying_df = pd.DataFrame()
    for quarter in ["Q1", "Q2", "Q3", "Q4"]:
        quarter_df = read_parquet_from_s3(
            s3_client,
            f"{S3_GOLD_PREFIX}/lobbying/fact_lobbying_activity/year={year}/quarter={quarter}/data.parquet"
        )
        if not quarter_df.empty:
            fact_lobbying_df = pd.concat([fact_lobbying_df, quarter_df], ignore_index=True)

    if bill_lobbying_df.empty or member_bill_df.empty:
        logger.error("Required data tables not found")
        return pd.DataFrame()

    # Filter member_bill to current congress
    member_bill_df = member_bill_df[member_bill_df["congress"] == congress]

    connections = []

    # Connection Type 1: Direct Bill Connection (100 points)
    # Member sponsored/cosponsored a bill that was lobbied
    logger.info("Computing direct bill connections...")
    bill_connections = member_bill_df.merge(
        bill_lobbying_df[["bill_id", "client_names", "registrant_names", "total_lobbying_spend", "top_issue_codes"]],
        on="bill_id",
        how="inner"
    )

    for _, row in bill_connections.iterrows():
        for client in row["client_names"]:
            connections.append({
                "member_bioguide_id": row["member_bioguide_id"],
                "client_name": client,
                "bill_id": row["bill_id"],
                "connection_type": "direct_bill",
                "connection_score": 100,
                "details": {
                    "role": row["role_type"],
                    "lobbying_spend": row["total_lobbying_spend"],
                    "issue_codes": row["top_issue_codes"]
                }
            })

    logger.info(f"Found {len(connections)} direct bill connections")

    # Connection Type 2: Contributions (30 points)
    # Lobbyist contributed to member's campaign
    logger.info("Computing contribution connections...")
    if not contributions_df.empty and not lobbyists_df.empty:
        # Match contributions to members by honoree name
        # Note: This requires fuzzy matching in production; using exact match for now
        contributions_with_lobbyist = contributions_df.merge(
            lobbyists_df[["lobbyist_id", "client_id", "registrant_id"]],
            on="lobbyist_id",
            how="left"
        )

        for _, row in contributions_with_lobbyist.iterrows():
            if row["honoree_name"]:  # Has a recipient
                connections.append({
                    "member_bioguide_id": None,  # Would need member lookup by name
                    "member_name": row["honoree_name"],
                    "lobbyist_id": row["lobbyist_id"],
                    "client_id": row["client_id"],
                    "registrant_id": row["registrant_id"],
                    "connection_type": "contribution",
                    "connection_score": 30,
                    "details": {
                        "amount": row["amount"],
                        "date": row["date"]
                    }
                })

        logger.info(f"Found {len([c for c in connections if c['connection_type'] == 'contribution'])} contribution connections")

    # Connection Type 3: Issue Overlap (10 points)
    # Member's sponsored bills + lobbying activity share same issue codes
    # (This would require bill_industry_tags to be computed)

    # Convert to DataFrame
    connections_df = pd.DataFrame(connections)

    if connections_df.empty:
        logger.warning("No connections found")
        return pd.DataFrame()

    # Aggregate connections by member-client pair
    logger.info("Aggregating connections...")

    agg_connections = connections_df.groupby(
        ["member_bioguide_id", "client_name"]
    ).agg({
        "connection_score": "sum",
        "bill_id": lambda x: list(x.dropna().unique()),
        "connection_type": lambda x: list(x.unique())
    }).reset_index()

    agg_connections.columns = [
        "member_bioguide_id",
        "client_name",
        "total_connection_score",
        "bills_in_common",
        "connection_types"
    ]

    # Add metadata
    agg_connections["year"] = year
    agg_connections["congress"] = congress
    agg_connections["dt_computed"] = datetime.utcnow().isoformat()

    # Sort by connection score
    agg_connections = agg_connections.sort_values("total_connection_score", ascending=False)

    logger.info(f"Computed {len(agg_connections)} member-client connection pairs")
    return agg_connections


def write_gold_table(df: pd.DataFrame, year: int) -> None:
    """Write DataFrame to Gold Parquet table."""
    if df.empty:
        logger.warning("No data to write")
        return

    s3_key = f"{S3_GOLD_PREFIX}/lobbying/agg_member_lobbyist_connections/year={year}/agg_member_lobbyist_connections.parquet"
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

    logger.info(f"Wrote {len(df)} member-lobbyist connections to {s3_key}")


def main():
    parser = argparse.ArgumentParser(description="Compute member-lobbyist network aggregate")
    parser.add_argument("--year", type=int, required=True, help="Filing year")
    parser.add_argument("--congress", type=int, required=True, help="Congress number (e.g., 118)")
    args = parser.parse_args()

    logger.info(f"Computing member-lobbyist network for year {args.year}, Congress {args.congress}")

    s3_client = boto3.client("s3")
    df = compute_network(s3_client, args.year, args.congress)

    if df.empty:
        logger.warning("No network connections computed")
        sys.exit(0)

    write_gold_table(df, args.year)

    # Print summary
    logger.info(f"\n{'='*60}")
    logger.info("SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"Total connections: {len(df)}")
    logger.info(f"Unique members: {df['member_bioguide_id'].nunique()}")
    logger.info(f"Unique clients: {df['client_name'].nunique()}")
    logger.info(f"Average connection score: {df['total_connection_score'].mean():.1f}")
    logger.info(f"\nTop 10 member-client connections:")
    top_connections = df.head(10)[["member_bioguide_id", "client_name", "total_connection_score", "connection_types"]]
    for _, row in top_connections.iterrows():
        logger.info(
            f"  {row['member_bioguide_id']} + {row['client_name']}: "
            f"{row['total_connection_score']} points ({', '.join(row['connection_types'])})"
        )


if __name__ == "__main__":
    main()
